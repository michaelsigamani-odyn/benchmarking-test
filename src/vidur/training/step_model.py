from dataclasses import dataclass

from .devices import resolve_device_profile
from .interface import LoraStepModel
from .predictors import predict_ms
from .types import LoraAdapterConfig, MemoryBreakdown, ModelConfig, PredictorBundle, StepPrediction, StepRequest, StepTimeBreakdown

GB = float(1024**3)
DTYPE_BYTES = {"bf16": 2.0, "fp16": 2.0, "fp32": 4.0}


@dataclass(frozen=True)
class AnalyticalLoraStepModel(LoraStepModel):
    bundle: PredictorBundle

    def predict_step(self, request: StepRequest, dataset_tokens: int) -> StepPrediction:
        step_time = predict_step_time(self.bundle, request)
        memory = predict_peak_memory(self.bundle, request)
        return assemble_prediction(request, dataset_tokens, step_time, memory)


def predict_step_time(bundle: PredictorBundle, request: StepRequest) -> StepTimeBreakdown:
    forward_ms = sum_forward_ms(bundle, request)
    backward_ms = sum_backward_ms(bundle, request)
    recompute_ms = forward_ms * recompute_factor(request)
    optimizer_ms = optimizer_ms_for_adapter(bundle, request)
    return StepTimeBreakdown(forward_ms, backward_ms, recompute_ms, optimizer_ms, fitted_overhead(bundle, request.device))


def sum_forward_ms(bundle: PredictorBundle, request: StepRequest) -> float:
    layers = request.model.num_hidden_layers
    return layers * (attention_ms(bundle, request, "forward") + mlp_ms(bundle, request, "forward"))


def sum_backward_ms(bundle: PredictorBundle, request: StepRequest) -> float:
    layers = request.model.num_hidden_layers
    return layers * (attention_ms(bundle, request, "backward") + mlp_ms(bundle, request, "backward"))


def attention_ms(bundle: PredictorBundle, request: StepRequest, phase: str) -> float:
    m = request.global_batch_size * request.sequence_length
    hidden = request.model.hidden_size
    return predict_ms(bundle, "attention", phase, request.dtype, m, hidden, hidden)


def mlp_ms(bundle: PredictorBundle, request: StepRequest, phase: str) -> float:
    m = request.global_batch_size * request.sequence_length
    hidden = request.model.hidden_size
    inter = request.model.intermediate_size
    proj = predict_ms(bundle, "base_linear", phase, request.dtype, m, hidden, inter)
    return proj + predict_ms(bundle, "base_linear", phase, request.dtype, m, inter, hidden)


def recompute_factor(request: StepRequest) -> float:
    return 0.35 if request.checkpointing else 0.0


def optimizer_ms_for_adapter(bundle: PredictorBundle, request: StepRequest) -> float:
    adapter_params = adapter_parameter_count(request.model, request.lora)
    return predict_ms(bundle, "adamw", "step", request.dtype, adapter_params, 1, 1)


def fitted_overhead(bundle: PredictorBundle, device: str) -> float:
    return float(bundle.fitted_overhead_ms.get(device, 0.0))


def predict_peak_memory(bundle: PredictorBundle, request: StepRequest) -> MemoryBreakdown:
    base_weights = to_gb(request.model.parameter_count * dtype_bytes(request.dtype))
    adapter_weights = to_gb(adapter_parameter_count(request.model, request.lora) * dtype_bytes(request.dtype))
    optimizer_states = to_gb(adapter_parameter_count(request.model, request.lora) * 8.0)
    gradients = to_gb(adapter_parameter_count(request.model, request.lora) * dtype_bytes(request.dtype))
    activations = activation_gb(bundle, request)
    return MemoryBreakdown(base_weights, adapter_weights, optimizer_states, gradients, activations, 0.25)


def activation_gb(bundle: PredictorBundle, request: StepRequest) -> float:
    tokens = request.global_batch_size * request.sequence_length
    hidden = request.model.hidden_size * request.model.num_hidden_layers
    factor = bundle.activation_factor.get("checkpoint_on" if request.checkpointing else "checkpoint_off", 10.0)
    return to_gb(tokens * hidden * dtype_bytes(request.dtype) * factor)


def adapter_parameter_count(model: ModelConfig, lora: LoraAdapterConfig) -> int:
    targets = max(len(lora.target_modules), 1)
    per_layer = targets * lora.rank * (model.hidden_size + model.hidden_size)
    return model.num_hidden_layers * per_layer


def dtype_bytes(dtype: str) -> float:
    if dtype not in DTYPE_BYTES:
        raise ValueError(f"unsupported dtype {dtype!r}")
    return DTYPE_BYTES[dtype]


def to_gb(bytes_value: float) -> float:
    return float(bytes_value / GB)


def assemble_prediction(request: StepRequest, dataset_tokens: int, step_time: StepTimeBreakdown, memory: MemoryBreakdown) -> StepPrediction:
    step_seconds = max(step_time.total_ms() / 1000.0, 1e-9)
    tokens_per_step = request.global_batch_size * request.sequence_length
    device = resolve_device_profile(request.device)
    return StepPrediction(step_time, memory, memory.total_gb(), tokens_per_step / step_seconds, epoch_seconds(dataset_tokens, tokens_per_step, step_seconds), memory.total_gb() <= device.memory_gb)


def epoch_seconds(dataset_tokens: int, tokens_per_step: int, step_seconds: float) -> float:
    return (dataset_tokens / max(tokens_per_step, 1)) * step_seconds

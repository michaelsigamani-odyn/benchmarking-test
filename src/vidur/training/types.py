from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ModelConfig:
    name: str
    hidden_size: int
    intermediate_size: int
    num_hidden_layers: int
    num_attention_heads: int
    vocab_size: int
    parameter_count: int


@dataclass(frozen=True)
class LoraAdapterConfig:
    rank: int
    alpha: int
    target_modules: Tuple[str, ...]
    dropout: float


@dataclass(frozen=True)
class StepRequest:
    model: ModelConfig
    global_batch_size: int
    sequence_length: int
    lora: LoraAdapterConfig
    checkpointing: bool
    dtype: str
    device: str


@dataclass(frozen=True)
class StepTimeBreakdown:
    forward_ms: float
    backward_ms: float
    recompute_ms: float
    optimizer_ms: float
    overhead_ms: float

    def total_ms(self) -> float:
        return self.forward_ms + self.backward_ms + self.recompute_ms + self.optimizer_ms + self.overhead_ms


@dataclass(frozen=True)
class MemoryBreakdown:
    base_weights_gb: float
    adapter_weights_gb: float
    optimizer_states_gb: float
    gradients_gb: float
    activations_gb: float
    miscellaneous_gb: float

    def total_gb(self) -> float:
        return self.base_weights_gb + self.adapter_weights_gb + self.optimizer_states_gb + self.gradients_gb + self.activations_gb + self.miscellaneous_gb


@dataclass(frozen=True)
class StepPrediction:
    step_time: StepTimeBreakdown
    memory: MemoryBreakdown
    peak_memory_gb: float
    tokens_per_second: float
    epoch_seconds: float
    feasible: bool


@dataclass(frozen=True)
class OpProfilePoint:
    op_name: str
    phase: str
    dtype: str
    m: int
    n: int
    k: int
    batch_size: int
    sequence_length: int
    wall_ms: float
    compile_ms: float
    warmup_ms: float
    kernel_ms: float
    residual_ms: float
    ok: bool
    error: str


@dataclass(frozen=True)
class OpPredictor:
    op_name: str
    phase: str
    intercept_ms: float
    flop_coeff_ms: float


@dataclass(frozen=True)
class PredictorBundle:
    predictors: Dict[str, OpPredictor]
    fitted_overhead_ms: Dict[str, float]
    activation_factor: Dict[str, float]


@dataclass(frozen=True)
class ValidationRow:
    model: str
    device: str
    batch_size: int
    sequence_length: int
    rank: int
    predicted_step_ms: float
    measured_step_ms: float
    predicted_peak_gb: float
    measured_peak_gb: float


def op_key(op_name: str, phase: str, dtype: str) -> str:
    return f"{op_name}:{phase}:{dtype}"


def flatten_validation(rows: List[ValidationRow]) -> List[Dict[str, float | int | str]]:
    return [
        {
            "model": row.model,
            "device": row.device,
            "batch_size": row.batch_size,
            "sequence_length": row.sequence_length,
            "rank": row.rank,
            "predicted_step_ms": row.predicted_step_ms,
            "measured_step_ms": row.measured_step_ms,
            "predicted_peak_gb": row.predicted_peak_gb,
            "measured_peak_gb": row.measured_peak_gb,
        }
        for row in rows
    ]

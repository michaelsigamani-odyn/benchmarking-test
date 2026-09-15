import json
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Optional

from .devices import resolve_device_profile
from .step_model import AnalyticalLoraStepModel
from .types import PredictorBundle, StepPrediction, StepRequest, StepTimeBreakdown


@dataclass(frozen=True)
class NeusightSettings:
    predictor_name: str
    predictor_path: Path
    device_config_path: Path
    model_config_path: Path
    tile_dataset_dir: Path | str
    options: str
    repo_root: Optional[Path]


@dataclass(frozen=True)
class UnifiedPrediction:
    prediction: StepPrediction
    backend: str
    analytical_step_ms: float
    neusight_step_ms: Optional[float]
    hybrid_analytical_weight: float


NeusightRunner = Callable[[NeusightSettings, StepRequest], float]


@dataclass(frozen=True)
class UnifiedLoraPredictor:
    bundle: PredictorBundle
    backend: str
    hybrid_analytical_weight: float
    neusight_settings: Optional[NeusightSettings] = None
    neusight_runner: Optional[NeusightRunner] = None

    def predict_step(self, request: StepRequest, dataset_tokens: int) -> UnifiedPrediction:
        analytical = AnalyticalLoraStepModel(self.bundle).predict_step(request, dataset_tokens)
        analytical_step_ms = analytical.step_time.total_ms()
        neusight_step_ms = predict_neusight_ms(self.neusight_settings, self.neusight_runner, request)
        selected_ms = select_step_ms(self.backend, analytical_step_ms, neusight_step_ms, self.hybrid_analytical_weight)
        return build_unified_prediction(request, dataset_tokens, analytical, selected_ms, self.backend, analytical_step_ms, neusight_step_ms, self.hybrid_analytical_weight)


def select_step_ms(backend: str, analytical_step_ms: float, neusight_step_ms: Optional[float], hybrid_analytical_weight: float) -> float:
    if backend == "analytical":
        return analytical_step_ms
    if backend == "neusight":
        return require_neusight(neusight_step_ms)
    return blend_step_ms(analytical_step_ms, require_neusight(neusight_step_ms), hybrid_analytical_weight)


def build_unified_prediction(request: StepRequest, dataset_tokens: int, analytical: StepPrediction, selected_step_ms: float, backend: str, analytical_step_ms: float, neusight_step_ms: Optional[float], hybrid_analytical_weight: float) -> UnifiedPrediction:
    step_time = rewrite_step_time(analytical.step_time, selected_step_ms)
    prediction = replace_time_outputs(request, dataset_tokens, analytical, step_time)
    return UnifiedPrediction(prediction, backend, analytical_step_ms, neusight_step_ms, hybrid_analytical_weight)


def replace_time_outputs(request: StepRequest, dataset_tokens: int, analytical: StepPrediction, step_time: StepTimeBreakdown) -> StepPrediction:
    step_seconds = max(step_time.total_ms() / 1000.0, 1e-9)
    tokens_per_step = request.global_batch_size * request.sequence_length
    epoch_seconds = (dataset_tokens / max(tokens_per_step, 1)) * step_seconds
    return StepPrediction(step_time, analytical.memory, analytical.peak_memory_gb, tokens_per_step / step_seconds, epoch_seconds, is_feasible(request.device, analytical.peak_memory_gb))


def rewrite_step_time(step_time: StepTimeBreakdown, total_step_ms: float) -> StepTimeBreakdown:
    base_total = max(step_time.total_ms(), 1e-9)
    scale = max(total_step_ms, 0.0) / base_total
    return StepTimeBreakdown(step_time.forward_ms * scale, step_time.backward_ms * scale, step_time.recompute_ms * scale, step_time.optimizer_ms * scale, step_time.overhead_ms * scale)


def is_feasible(device: str, peak_memory_gb: float) -> bool:
    return peak_memory_gb <= resolve_device_profile(device).memory_gb


def blend_step_ms(analytical_step_ms: float, neusight_step_ms: float, hybrid_analytical_weight: float) -> float:
    weight = clamp(hybrid_analytical_weight, 0.0, 1.0)
    return (weight * analytical_step_ms) + ((1.0 - weight) * neusight_step_ms)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def require_neusight(neusight_step_ms: Optional[float]) -> float:
    if neusight_step_ms is None:
        raise ValueError("NeuSight prediction requested but no NeuSight settings were provided")
    return neusight_step_ms


def predict_neusight_ms(settings: Optional[NeusightSettings], runner: Optional[NeusightRunner], request: StepRequest) -> Optional[float]:
    if settings is None:
        return None
    predictor = runner or run_neusight
    return predictor(settings, request)


def run_neusight(settings: NeusightSettings, request: StepRequest) -> float:
    append_repo_to_sys_path(settings.repo_root)
    from neusight import NeusightPredictor

    predictor = NeusightPredictor(settings.predictor_name, str(settings.predictor_path), str(settings.tile_dataset_dir))
    with TemporaryDirectory(prefix="unified-neusight-") as temp_dir:
        predictor.predict(device_config_path=str(settings.device_config_path), model_config_path=str(settings.model_config_path), sequence_length=request.sequence_length, batch_size=request.global_batch_size, execution_type="train", result_dir=temp_dir, options=settings.options, use_lora=True, lora_r=request.lora.rank, lora_alpha=request.lora.alpha, lora_dropout=request.lora.dropout, lora_target_modules=list(request.lora.target_modules), lora_trace_with_peft=True)
        return read_neusight_latency(Path(temp_dir))


def append_repo_to_sys_path(repo_root: Optional[Path]) -> None:
    if repo_root is None:
        return
    resolved = str(repo_root.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def read_neusight_latency(result_dir: Path) -> float:
    files = sorted(result_dir.glob("prediction/**/*.json"))
    if not files:
        raise FileNotFoundError(f"No NeuSight prediction JSON found under {result_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    return float(payload["e2e_latency"])

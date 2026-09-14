import argparse
import json
from pathlib import Path
from typing import Dict, List

from .predictors import load_bundle, save_bundle
from .step_model import predict_peak_memory, predict_step_time
from .types import LoraAdapterConfig, ModelConfig, PredictorBundle, StepRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit overhead and activation factors from measured validation cases")
    parser.add_argument("--predictor-bundle", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output-bundle", required=True)
    parser.add_argument("--output-calibration", required=True)
    return parser.parse_args()


def load_cases(path: Path) -> List[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_request(case: dict) -> StepRequest:
    model = ModelConfig(**case["model"])
    lora = LoraAdapterConfig(case["rank"], case["alpha"], tuple(case["target_modules"]), case.get("dropout", 0.05))
    return StepRequest(model, case["batch_size"], case["sequence_length"], lora, case.get("checkpointing", False), case.get("dtype", "bf16"), case["device"])


def fit_bundle(bundle: PredictorBundle, cases: List[dict]) -> tuple[PredictorBundle, Dict]:
    overhead = fit_overhead(bundle, cases)
    activation = fit_activation(bundle, cases)
    fitted = PredictorBundle(bundle.predictors, overhead, activation)
    return fitted, calibration_report(overhead, activation)


def fit_overhead(bundle: PredictorBundle, cases: List[dict]) -> Dict[str, float]:
    residuals: Dict[str, List[float]] = {}
    trial = PredictorBundle(bundle.predictors, {}, bundle.activation_factor)
    for case in cases:
        request = build_request(case)
        predicted = predict_step_time(trial, request).total_ms()
        residual = float(case["measured_step_ms"]) - predicted
        residuals.setdefault(request.device, []).append(residual)
    return {device: max(sum(values) / max(len(values), 1), 0.0) for device, values in residuals.items()}


def fit_activation(bundle: PredictorBundle, cases: List[dict]) -> Dict[str, float]:
    states = {"checkpoint_off": [], "checkpoint_on": []}
    trial = PredictorBundle(bundle.predictors, bundle.fitted_overhead_ms, {})
    for case in cases:
        request = build_request(case)
        baseline = predict_peak_memory(trial, request)
        state = "checkpoint_on" if request.checkpointing else "checkpoint_off"
        target = float(case["measured_peak_gb"])
        denom = max(baseline.activations_gb, 1e-9)
        states[state].append(max((target - non_activation_gb(baseline)) / denom, 0.01))
    return {name: average_or_default(values, bundle.activation_factor.get(name, 10.0)) for name, values in states.items()}


def non_activation_gb(memory) -> float:
    return memory.total_gb() - memory.activations_gb


def average_or_default(values: List[float], fallback: float) -> float:
    return sum(values) / len(values) if values else fallback


def calibration_report(overhead: Dict[str, float], activation: Dict[str, float]) -> Dict:
    return {"fitted_overhead_ms": overhead, "fitted_activation_factor": activation}


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    bundle = load_bundle(Path(args.predictor_bundle))
    fitted_bundle, report = fit_bundle(bundle, load_cases(Path(args.cases)))
    save_bundle(fitted_bundle, Path(args.output_bundle))
    write_json(Path(args.output_calibration), report)


if __name__ == "__main__":
    main()

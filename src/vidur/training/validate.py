import argparse
import json
from pathlib import Path
from typing import List

from .predictors import load_bundle
from .step_model import AnalyticalLoraStepModel
from .types import LoraAdapterConfig, ModelConfig, StepRequest, ValidationRow, flatten_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate predicted vs measured LoRA step-time and memory")
    parser.add_argument("--predictor-bundle", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_cases(path: Path) -> List[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def model_from_case(case: dict) -> ModelConfig:
    return ModelConfig(**case["model"])


def request_from_case(case: dict) -> StepRequest:
    lora = LoraAdapterConfig(case["rank"], case["alpha"], tuple(case["target_modules"]), case.get("dropout", 0.05))
    return StepRequest(model_from_case(case), case["batch_size"], case["sequence_length"], lora, case.get("checkpointing", False), case.get("dtype", "bf16"), case["device"])


def validate_cases(bundle_path: Path, cases: List[dict]) -> List[ValidationRow]:
    model = AnalyticalLoraStepModel(load_bundle(bundle_path))
    return [validate_case(model, case) for case in cases]


def validate_case(model: AnalyticalLoraStepModel, case: dict) -> ValidationRow:
    prediction = model.predict_step(request_from_case(case), case["dataset_tokens"])
    return ValidationRow(case["model"]["name"], case["device"], case["batch_size"], case["sequence_length"], case["rank"], prediction.step_time.total_ms(), case["measured_step_ms"], prediction.peak_memory_gb, case["measured_peak_gb"])


def write_rows(path: Path, rows: List[ValidationRow]) -> None:
    payload = {"rows": flatten_validation(rows), "step_mae_percent": mae_percent([row.predicted_step_ms for row in rows], [row.measured_step_ms for row in rows]), "memory_mae_percent": mae_percent([row.predicted_peak_gb for row in rows], [row.measured_peak_gb for row in rows])}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def mae_percent(predicted: List[float], measured: List[float]) -> float:
    errors = [abs(p - m) / max(m, 1e-9) * 100.0 for p, m in zip(predicted, measured)]
    return sum(errors) / max(len(errors), 1)


def main() -> None:
    args = parse_args()
    rows = validate_cases(Path(args.predictor_bundle), load_cases(Path(args.cases)))
    write_rows(Path(args.output), rows)


if __name__ == "__main__":
    main()

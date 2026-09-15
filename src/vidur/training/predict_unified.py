import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .predict import build_request, load_model_config
from .predictors import load_bundle
from .unified_predictor import NeusightSettings, UnifiedLoraPredictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified LoRA fine-tuning predictor (Analytical + NeuSight)")
    parser.add_argument("--predictor-bundle", required=True)
    parser.add_argument("--model-config", required=True)
    parser.add_argument("--device", required=True, choices=["dgx_spark_gb10", "radeon_8060s"])
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--seq-len", required=True, type=int)
    parser.add_argument("--lora-rank", required=True, type=int)
    parser.add_argument("--lora-alpha", required=True, type=int)
    parser.add_argument("--lora-target-modules", required=True)
    parser.add_argument("--lora-dropout", default=0.05, type=float)
    parser.add_argument("--checkpointing", action="store_true")
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--dataset-tokens", required=True, type=int)
    parser.add_argument("--backend", default="hybrid", choices=["analytical", "neusight", "hybrid"])
    parser.add_argument("--hybrid-analytical-weight", default=0.6, type=float)
    parser.add_argument("--neusight-predictor-name", default="neusight")
    parser.add_argument("--neusight-predictor-path", default="")
    parser.add_argument("--neusight-device-config", default="")
    parser.add_argument("--neusight-model-config", default="")
    parser.add_argument("--neusight-tile-dataset-dir", default="")
    parser.add_argument("--neusight-options", default="")
    parser.add_argument("--neusight-repo-root", default="")
    parser.add_argument("--json-output", default="")
    return parser.parse_args()


def build_neusight_settings(args: argparse.Namespace) -> NeusightSettings | None:
    if args.backend == "analytical":
        return None
    return NeusightSettings(args.neusight_predictor_name, required_path(args.neusight_predictor_path), required_path(args.neusight_device_config), required_path(args.neusight_model_config), args.neusight_tile_dataset_dir, args.neusight_options, optional_path(args.neusight_repo_root))


def required_path(raw: str) -> Path:
    path = Path(raw)
    if not raw or not path.exists():
        raise FileNotFoundError(f"Required path does not exist: {raw!r}")
    return path


def optional_path(raw: str) -> Path | None:
    return Path(raw) if raw else None


def print_prediction(payload: dict) -> None:
    print(f"backend={payload['backend']}")
    print(f"analytical_step_ms={payload['analytical_step_ms']:.3f}")
    print(f"neusight_step_ms={payload['neusight_step_ms'] if payload['neusight_step_ms'] is not None else 'n/a'}")
    print(f"total_step_ms={payload['prediction']['step_time']['forward_ms'] + payload['prediction']['step_time']['backward_ms'] + payload['prediction']['step_time']['recompute_ms'] + payload['prediction']['step_time']['optimizer_ms'] + payload['prediction']['step_time']['overhead_ms']:.3f}")
    print(f"peak_memory_gb={payload['prediction']['peak_memory_gb']:.3f}")
    print(f"tokens_per_second={payload['prediction']['tokens_per_second']:.3f}")
    print(f"epoch_seconds={payload['prediction']['epoch_seconds']:.3f}")
    print(f"feasible={payload['prediction']['feasible']}")


def to_payload(unified) -> dict:
    return {
        "backend": unified.backend,
        "hybrid_analytical_weight": unified.hybrid_analytical_weight,
        "analytical_step_ms": unified.analytical_step_ms,
        "neusight_step_ms": unified.neusight_step_ms,
        "prediction": asdict(unified.prediction),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    model = load_model_config(Path(args.model_config))
    request = build_request(args, model)
    predictor = UnifiedLoraPredictor(load_bundle(Path(args.predictor_bundle)), args.backend, args.hybrid_analytical_weight, build_neusight_settings(args))
    payload = to_payload(predictor.predict_step(request, args.dataset_tokens))
    print_prediction(payload)
    if args.json_output:
        write_json(Path(args.json_output), payload)


if __name__ == "__main__":
    main()

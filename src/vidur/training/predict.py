import argparse
import json
from pathlib import Path

from .predictors import load_bundle
from .step_model import AnalyticalLoraStepModel
from .types import LoraAdapterConfig, ModelConfig, StepRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict LoRA fine-tuning step-time and memory")
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
    return parser.parse_args()


def load_model_config(path: Path) -> ModelConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ModelConfig(**payload)


def parse_targets(raw_targets: str) -> tuple[str, ...]:
    return tuple(target.strip() for target in raw_targets.split(",") if target.strip())


def build_request(args: argparse.Namespace, model: ModelConfig) -> StepRequest:
    lora = LoraAdapterConfig(args.lora_rank, args.lora_alpha, parse_targets(args.lora_target_modules), args.lora_dropout)
    return StepRequest(model, args.batch_size, args.seq_len, lora, args.checkpointing, args.dtype, args.device)


def print_prediction(prediction) -> None:
    print(f"forward_ms={prediction.step_time.forward_ms:.3f}")
    print(f"backward_ms={prediction.step_time.backward_ms:.3f}")
    print(f"recompute_ms={prediction.step_time.recompute_ms:.3f}")
    print(f"optimizer_ms={prediction.step_time.optimizer_ms:.3f}")
    print(f"overhead_ms={prediction.step_time.overhead_ms:.3f}")
    print(f"total_step_ms={prediction.step_time.total_ms():.3f}")
    print(f"peak_memory_gb={prediction.peak_memory_gb:.3f}")
    print(f"tokens_per_second={prediction.tokens_per_second:.3f}")
    print(f"epoch_seconds={prediction.epoch_seconds:.3f}")
    print(f"feasible={prediction.feasible}")


def main() -> None:
    args = parse_args()
    model = load_model_config(Path(args.model_config))
    bundle = load_bundle(Path(args.predictor_bundle))
    prediction = AnalyticalLoraStepModel(bundle).predict_step(build_request(args, model), args.dataset_tokens)
    print_prediction(prediction)


if __name__ == "__main__":
    main()

import argparse
from pathlib import Path

from .runner import run_training_profiles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile LoRA fine-tuning kernels")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--warmup-steps", default=10, type=int)
    parser.add_argument("--measure-steps", default=30, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_training_profiles(Path(args.output_dir), args.dtype, args.device, args.warmup_steps, args.measure_steps)


if __name__ == "__main__":
    main()

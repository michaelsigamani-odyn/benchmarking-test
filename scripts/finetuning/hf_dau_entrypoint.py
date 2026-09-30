from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EntrypointConfig:
    model_id: str
    dataset_path: str
    output_dir: str
    seed: int
    stop_step: int
    max_steps: int
    per_device_batch_size: int


def parse_args() -> EntrypointConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--stop-step", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--per-device-batch-size", type=int, default=1)
    args = parser.parse_args()
    return EntrypointConfig(args.model_id, args.dataset_path, args.output_dir, args.seed, args.stop_step, args.max_steps, args.per_device_batch_size)


def run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True)


def install_deps() -> None:
    run([sys.executable, "-m", "pip", "install", "-q", "torch", "transformers", "datasets", "peft", "accelerate", "safetensors"])


def train_cmd(cfg: EntrypointConfig) -> List[str]:
    return [sys.executable, "/workspace/scripts/finetuning/train_lora_migration.py", "--model-id", cfg.model_id, "--dataset-path", cfg.dataset_path, "--output-dir", cfg.output_dir, "--stop-step", str(cfg.stop_step), "--max-steps", str(cfg.max_steps), "--per-device-batch-size", str(cfg.per_device_batch_size), "--seed", str(cfg.seed)]


def main() -> None:
    cfg = parse_args()
    install_deps()
    run(train_cmd(cfg))


if __name__ == "__main__":
    main()

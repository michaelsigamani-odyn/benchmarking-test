import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM


@dataclass(frozen=True)
class RunStats:
    model_id: str
    attention_impl: str
    dtype: str
    step_time_ms: float
    peak_memory_gb: float
    tokens_per_second: float
    measured_steps: int
    warmup_steps_skipped: int
    torch_version: str
    transformers_version: str
    peft_version: str


class RandomTokenDataset(Dataset):
    def __init__(self, vocab_size: int, sequence_length: int, rows: int):
        self._vocab_size, self._sequence_length, self._rows = vocab_size, sequence_length, rows

    def __len__(self) -> int:
        return self._rows

    def __getitem__(self, _: int) -> Dict[str, torch.Tensor]:
        tokens = torch.randint(0, self._vocab_size, (self._sequence_length,), dtype=torch.long)
        return {"input_ids": tokens, "labels": tokens.clone(), "attention_mask": torch.ones_like(tokens)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reference LoRA training run with measured step-time and peak memory")
    parser.add_argument("--model-id", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    parser.add_argument("--batch-size", default=1, type=int)
    parser.add_argument("--seq-len", default=1024, type=int)
    parser.add_argument("--lora-rank", default=16, type=int)
    parser.add_argument("--lora-alpha", default=32, type=int)
    parser.add_argument("--lora-dropout", default=0.05, type=float)
    parser.add_argument("--lora-target-modules", default="q_proj,k_proj,v_proj,o_proj")
    parser.add_argument("--steps", default=40, type=int)
    parser.add_argument("--warmup-steps", default=5, type=int)
    parser.add_argument("--learning-rate", default=2e-4, type=float)
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def parse_dtype(raw: str) -> torch.dtype:
    mapping = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}
    return mapping[raw]


def select_device() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA or ROCm device is required")
    return torch.device("cuda")


def load_model(model_id: str, dtype: torch.dtype, device: torch.device) -> Tuple[torch.nn.Module, str]:
    kwargs = {"torch_dtype": dtype, "device_map": {"": device.index or 0}, "attn_implementation": "flash_attention_2"}
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, **kwargs), "flash_attention_2"
    except Exception:
        fallback = dict(kwargs)
        fallback["attn_implementation"] = "sdpa"
        return AutoModelForCausalLM.from_pretrained(model_id, **fallback), "sdpa"


def configure_lora(model: torch.nn.Module, args: argparse.Namespace) -> torch.nn.Module:
    target_modules = tuple(token.strip() for token in args.lora_target_modules.split(",") if token.strip())
    config = LoraConfig(task_type=TaskType.CAUSAL_LM, r=args.lora_rank, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout, target_modules=target_modules)
    return get_peft_model(model, config)


def build_loader(model: torch.nn.Module, args: argparse.Namespace) -> DataLoader:
    dataset = RandomTokenDataset(model.config.vocab_size, args.seq_len, args.steps * args.batch_size)
    return DataLoader(dataset, batch_size=args.batch_size, shuffle=False)


def run_reference(model: torch.nn.Module, loader: DataLoader, args: argparse.Namespace, device: torch.device) -> Tuple[float, float, float]:
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    timings = loop_steps(model, loader, optimizer, args, device)
    return summarize_times(timings, args)


def loop_steps(model, loader, optimizer, args, device) -> List[float]:
    model.train()
    timings: List[float] = []
    for step, batch in enumerate(loader):
        if step >= args.steps:
            break
        timings.append(run_step(model, optimizer, move_batch(batch, device), args.dtype))
    return timings


def run_step(model, optimizer, batch, dtype_name: str) -> float:
    start = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast(device_type="cuda", dtype=parse_dtype(dtype_name), enabled=dtype_name != "fp32"):
        loss = model(**batch).loss
    loss.backward()
    optimizer.step()
    synchronize_device()
    return (time.perf_counter() - start) * 1000.0


def synchronize_device() -> None:
    torch.cuda.synchronize()


def move_batch(batch: Dict[str, torch.Tensor], device: torch.device) -> Dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


def summarize_times(step_times_ms: List[float], args: argparse.Namespace) -> Tuple[float, float, float]:
    measured = step_times_ms[args.warmup_steps:]
    if not measured:
        raise ValueError("warmup-steps must be smaller than total steps")
    mean_ms = statistics.fmean(measured)
    tokens_per_step = args.batch_size * args.seq_len
    elapsed_seconds = max(sum(measured) / 1000.0, 1e-9)
    return mean_ms, torch.cuda.max_memory_allocated() / float(1024**3), (tokens_per_step * len(measured)) / elapsed_seconds


def build_stats(args: argparse.Namespace, attention_impl: str, measured: Tuple[float, float, float]) -> RunStats:
    import peft
    import transformers

    return RunStats(args.model_id, attention_impl, args.dtype, measured[0], measured[1], measured[2], args.steps - args.warmup_steps, args.warmup_steps, torch.__version__, transformers.__version__, peft.__version__)


def write_stats(path: Path, stats: RunStats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    device = select_device()
    model, attention_impl = load_model(args.model_id, parse_dtype(args.dtype), device)
    model = configure_lora(model, args)
    torch.cuda.reset_peak_memory_stats()
    measured = run_reference(model, build_loader(model, args), args, device)
    write_stats(Path(args.output), build_stats(args, attention_impl, measured))


if __name__ == "__main__":
    main()

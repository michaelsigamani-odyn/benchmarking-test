import time
from pathlib import Path
from typing import List

import torch

from vidur.training.types import OpProfilePoint

from .io import write_profiles, write_unsupported
from .kernels import OpSpec, build_specs, make_kernel, parse_dtype


def run_training_profiles(output_dir: Path, dtype: str, device: str, warmup_steps: int = 10, measure_steps: int = 30) -> List[OpProfilePoint]:
    points = profile_specs(dtype, device, warmup_steps, measure_steps)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_profiles(output_dir / "profiles.csv", points)
    write_unsupported(output_dir / "unsupported.json", points)
    return points


def profile_specs(dtype: str, device: str, warmup_steps: int, measure_steps: int) -> List[OpProfilePoint]:
    specs = build_specs(hidden_sizes=[1024, 2048, 4096], batch_sizes=[1, 2, 4], sequence_lengths=[512, 1024, 2048])
    return [profile_spec(spec, dtype, device, warmup_steps, measure_steps) for spec in specs]


def profile_spec(spec: OpSpec, dtype: str, device_name: str, warmup_steps: int, measure_steps: int) -> OpProfilePoint:
    started = time.perf_counter()
    device = torch.device(device_name)
    try:
        kernel = make_kernel(spec, device, parse_dtype(dtype))
        compile_ms, warmup_ms, kernel_ms = timed_phases(kernel, device, warmup_steps, measure_steps)
        wall_ms = (time.perf_counter() - started) * 1000.0
        residual_ms = max(wall_ms - compile_ms - warmup_ms - kernel_ms, 0.0)
        return OpProfilePoint(spec.op_name, spec.phase, dtype, *spec.shape, spec.batch_size, spec.sequence_length, wall_ms, compile_ms, warmup_ms, kernel_ms, residual_ms, True, "")
    except Exception as exc:
        return OpProfilePoint(spec.op_name, spec.phase, dtype, *spec.shape, spec.batch_size, spec.sequence_length, 0.0, 0.0, 0.0, 0.0, 0.0, False, str(exc))


def timed_phases(kernel, device: torch.device, warmup_steps: int, measure_steps: int) -> tuple[float, float, float]:
    compile_ms = timed_call_ms(kernel, device)
    warmup_ms = average_ms([timed_call_ms(kernel, device) for _ in range(warmup_steps)])
    kernel_ms = average_ms([timed_call_ms(kernel, device) for _ in range(measure_steps)])
    return compile_ms, warmup_ms, kernel_ms


def timed_call_ms(kernel, device: torch.device) -> float:
    start = time.perf_counter()
    _ = kernel()
    synchronize_device(device)
    return (time.perf_counter() - start) * 1000.0


def synchronize_device(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def average_ms(values: List[float]) -> float:
    return sum(values) / max(len(values), 1)

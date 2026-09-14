from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

import torch

KernelCallable = Callable[[], torch.Tensor]


@dataclass(frozen=True)
class OpSpec:
    op_name: str
    phase: str
    shape: Tuple[int, int, int]
    batch_size: int
    sequence_length: int


def build_specs(hidden_sizes: Iterable[int], batch_sizes: Iterable[int], sequence_lengths: Iterable[int]) -> List[OpSpec]:
    return [spec for hidden in hidden_sizes for batch in batch_sizes for seq in sequence_lengths for spec in per_shape_specs(hidden, batch, seq)]


def per_shape_specs(hidden: int, batch: int, seq: int) -> List[OpSpec]:
    m = batch * seq
    shapes = [
        OpSpec("base_linear", "forward", (m, hidden, 4 * hidden), batch, seq),
        OpSpec("base_linear", "backward", (m, 4 * hidden, hidden), batch, seq),
        OpSpec("attention", "forward", (m, hidden, hidden), batch, seq),
        OpSpec("attention", "backward", (m, hidden, hidden), batch, seq),
        OpSpec("lora_a", "forward", (m, hidden, 64), batch, seq),
        OpSpec("lora_a", "backward", (m, 64, hidden), batch, seq),
        OpSpec("lora_b", "forward", (m, 64, hidden), batch, seq),
        OpSpec("lora_b", "backward", (m, hidden, 64), batch, seq),
        OpSpec("adamw", "step", (hidden * 64, 1, 1), batch, seq),
    ]
    return shapes


def make_kernel(spec: OpSpec, device: torch.device, dtype: torch.dtype) -> KernelCallable:
    kernels = {"forward": make_forward_kernel, "backward": make_backward_kernel, "step": make_optimizer_kernel}
    return kernels[spec.phase](spec, device, dtype)


def make_forward_kernel(spec: OpSpec, device: torch.device, dtype: torch.dtype) -> KernelCallable:
    lhs = torch.randn(spec.shape[0], spec.shape[1], device=device, dtype=dtype)
    rhs = torch.randn(spec.shape[1], spec.shape[2], device=device, dtype=dtype)
    return lambda: lhs @ rhs


def make_backward_kernel(spec: OpSpec, device: torch.device, dtype: torch.dtype) -> KernelCallable:
    lhs = torch.randn(spec.shape[0], spec.shape[1], device=device, dtype=dtype, requires_grad=True)
    rhs = torch.randn(spec.shape[1], spec.shape[2], device=device, dtype=dtype, requires_grad=True)
    return lambda: torch.autograd.grad((lhs @ rhs).square().mean(), (lhs, rhs), retain_graph=True)[0]


def make_optimizer_kernel(spec: OpSpec, device: torch.device, dtype: torch.dtype) -> KernelCallable:
    parameter = torch.nn.Parameter(torch.randn(spec.shape[0], device=device, dtype=dtype))
    optimizer = torch.optim.AdamW([parameter], lr=1e-4)
    return lambda: run_optimizer_step(parameter, optimizer)


def run_optimizer_step(parameter: torch.nn.Parameter, optimizer: torch.optim.AdamW) -> torch.Tensor:
    optimizer.zero_grad(set_to_none=True)
    loss = parameter.square().mean()
    loss.backward()
    optimizer.step()
    return loss


def parse_dtype(name: str) -> torch.dtype:
    lookup: Dict[str, torch.dtype] = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}
    return lookup[name]

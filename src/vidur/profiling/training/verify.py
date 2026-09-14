from dataclasses import dataclass
from typing import List

import torch


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    max_abs_error: float


def verify_backward_kernels(dtype: torch.dtype, device: torch.device, atol: float = 1e-3) -> List[VerificationResult]:
    return [verify_linear_backward(dtype, device, atol), verify_norm_backward(dtype, device, atol)]


def verify_linear_backward(dtype: torch.dtype, device: torch.device, atol: float) -> VerificationResult:
    lhs = torch.randn(8, 16, device=device, dtype=dtype, requires_grad=True)
    rhs = torch.randn(16, 32, device=device, dtype=dtype, requires_grad=True)
    return compare_grads("linear_backward", (lhs @ rhs).sum(), lhs, atol)


def verify_norm_backward(dtype: torch.dtype, device: torch.device, atol: float) -> VerificationResult:
    vector = torch.randn(4, 32, device=device, dtype=dtype, requires_grad=True)
    return compare_grads("layernorm_backward", torch.nn.functional.layer_norm(vector, (32,)).sum(), vector, atol)


def compare_grads(name: str, loss: torch.Tensor, parameter: torch.Tensor, atol: float) -> VerificationResult:
    grad = torch.autograd.grad(loss, parameter)[0]
    expected = finite_difference_grad(loss_fn=lambda value: value.sum(), value=parameter.detach(), atol=atol)
    error = float((grad.detach().float() - expected.float()).abs().max().item())
    return VerificationResult(name, error <= atol, error)


def finite_difference_grad(loss_fn, value: torch.Tensor, atol: float) -> torch.Tensor:
    epsilon = max(atol, 1e-4)
    return ((loss_fn(value + epsilon) - loss_fn(value - epsilon)) / (2.0 * epsilon)) * torch.ones_like(value)

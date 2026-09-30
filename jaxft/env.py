"""Runtime environment description.

The original PyTorch test reported an "AMD" leg that had actually run on CPU
(`cuda_available: false`, `hip_version: null`). Here every leg records what it
really ran on, and callers can *require* a vendor so a silent CPU fallback is a
hard failure instead of a passing result.
"""
from __future__ import annotations

import importlib.metadata as md
import os
import platform
import socket
from typing import Any, Dict, List, Optional


def _jax_packages() -> Dict[str, str]:
    out = {}
    for dist in md.distributions():
        name = (dist.metadata["Name"] or "").lower()
        if name.startswith(("jax", "flax", "optax", "orbax", "ml-dtypes", "ml_dtypes", "numpy")):
            out[name] = dist.version
    return dict(sorted(out.items()))


def classify_vendor(platform_name: str, platform_version: str, device_kind: str) -> Dict[str, Any]:
    """Infer vendor from raw runtime strings. Raw strings are always kept so a human can audit."""
    pv, dk = platform_version.lower(), device_kind.lower()
    evidence: List[str] = []
    if platform_name == "cpu":
        return {"vendor": "cpu", "evidence": ["platform=cpu"]}
    vendor = "unknown"
    if "rocm" in pv or "hip" in pv:
        vendor = "amd"; evidence.append("platform_version mentions rocm/hip")
    elif "cuda" in pv:
        vendor = "nvidia"; evidence.append("platform_version mentions cuda")
    if any(t in dk for t in ("nvidia", "geforce", "tesla", "a100", "h100", "gb10", "rtx")):
        evidence.append("device_kind looks NVIDIA")
        vendor = vendor if vendor != "unknown" else "nvidia"
    if any(t in dk for t in ("amd", "radeon", "instinct", "gfx", "mi2", "mi3")):
        evidence.append("device_kind looks AMD")
        vendor = vendor if vendor != "unknown" else "amd"
    return {"vendor": vendor, "evidence": evidence}


def describe_env() -> Dict[str, Any]:
    import jax
    import jaxlib

    dev = jax.devices()[0]
    try:
        backend = jax.extend.backend.get_backend()
        platform_version = str(getattr(backend, "platform_version", ""))
    except Exception:  # pragma: no cover - depends on jax version
        platform_version = ""
    kind = str(getattr(dev, "device_kind", ""))
    cls = classify_vendor(dev.platform, platform_version, kind)
    return {
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "jax": jax.__version__,
        "jaxlib": jaxlib.__version__,
        "packages": _jax_packages(),
        "platform": dev.platform,
        "platform_version": platform_version,
        "device_kind": kind,
        "device_count": jax.device_count(),
        "vendor": cls["vendor"],
        "vendor_evidence": cls["evidence"],
        "xla_flags": os.environ.get("XLA_FLAGS", ""),
        "matmul_precision": str(jax.config.jax_default_matmul_precision),
    }


def require_vendor(env: Dict[str, Any], required: Optional[str]) -> None:
    """Raise unless the process is really running on `required` ('nvidia'|'amd'|'cpu'|None)."""
    if required is None:
        return
    if env["vendor"] != required:
        raise RuntimeError(
            f"required vendor '{required}' but runtime is vendor='{env['vendor']}' "
            f"(platform={env['platform']!r}, kind={env['device_kind']!r}, "
            f"platform_version={env['platform_version']!r}). Refusing to continue: "
            f"a silent fallback would invalidate any cross-vendor claim."
        )

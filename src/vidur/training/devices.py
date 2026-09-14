from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DeviceProfile:
    name: str
    memory_gb: float
    bandwidth_gbps: float


def build_device_profiles() -> Dict[str, DeviceProfile]:
    return {
        "dgx_spark_gb10": DeviceProfile("dgx_spark_gb10", 128.0, 273.0),
        "radeon_8060s": DeviceProfile("radeon_8060s", 128.0, 256.0),
    }


def resolve_device_profile(device: str) -> DeviceProfile:
    profiles = build_device_profiles()
    if device not in profiles:
        raise ValueError(f"unknown device {device!r}")
    return profiles[device]

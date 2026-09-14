import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class MeasuredDevicePoint:
    device: str
    model_id: str
    batch_size: int
    sequence_length: int
    steps_executed: int
    step_time_ms: float
    peak_memory_gb: float
    dataset_tokens: int


def load_report(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_points(path: Path, batch_size: int, sequence_length: int) -> List[MeasuredDevicePoint]:
    report = load_report(path)
    return [section_point(report, "source_training", batch_size, sequence_length), section_point(report, "destination_training", batch_size, sequence_length)]


def section_point(report: Dict, section: str, batch_size: int, sequence_length: int) -> MeasuredDevicePoint:
    payload = report[section]
    steps = int(payload.get("steps_executed") or (payload["last_step"] - payload["first_step"]))
    step_ms = float(payload["training_runtime_seconds"]) * 1000.0 / max(steps, 1)
    peak_gb = float(payload["peak_accelerator_memory_bytes"]) / float(1024**3)
    return MeasuredDevicePoint(normalize_device(payload), report["run"]["model_id"], batch_size, sequence_length, steps, step_ms, peak_gb, int(payload.get("useful_training_tokens") or 0))


def normalize_device(payload: Dict) -> str:
    if "8060S" in str(payload.get("device_name", "")):
        return "radeon_8060s"
    if "GB10" in str(payload.get("device_name", "")):
        return "dgx_spark_gb10"
    raise ValueError(f"unsupported device mapping: {payload.get('device_name')!r}")


def extract_transfer_metrics(path: Path) -> Dict[str, float]:
    migration = load_report(path).get("migration", {})
    return {
        "iperf3_bps": float(migration.get("iperf3", {}).get("throughput_bits_per_second", 0.0)),
        "rsync_bps": float(migration.get("rsync", {}).get("throughput_bytes_per_second", 0.0)) * 8.0,
        "mooncake_bps": float(migration.get("mooncake", {}).get("throughput_bytes_per_second", 0.0)) * 8.0,
        "transfer_seconds": float(migration.get("transfer_seconds", 0.0)),
    }


def build_validation_case(points: List[MeasuredDevicePoint], rank: int, alpha: int, target_modules: List[str], model_config: Dict) -> List[Dict]:
    return [single_case(point, rank, alpha, target_modules, model_config) for point in points]


def single_case(point: MeasuredDevicePoint, rank: int, alpha: int, target_modules: List[str], model_config: Dict) -> Dict:
    return {
        "device": point.device,
        "dataset_tokens": point.dataset_tokens,
        "batch_size": point.batch_size,
        "sequence_length": point.sequence_length,
        "rank": rank,
        "alpha": alpha,
        "target_modules": target_modules,
        "dtype": "bf16",
        "checkpointing": False,
        "measured_step_ms": point.step_time_ms,
        "measured_peak_gb": point.peak_memory_gb,
        "model": model_config,
    }

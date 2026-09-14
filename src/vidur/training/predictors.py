import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from .types import OpPredictor, OpProfilePoint, PredictorBundle, op_key


def read_profile_points(path: Path) -> List[OpProfilePoint]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row_to_point(row) for row in rows]


def row_to_point(row: Dict[str, str]) -> OpProfilePoint:
    ok = row["ok"].strip().lower() in {"1", "true", "yes"}
    return OpProfilePoint(
        row["op_name"], row["phase"], row["dtype"], int(row["m"]), int(row["n"]), int(row["k"]),
        int(row["batch_size"]), int(row["sequence_length"]), float(row["wall_ms"]), float(row["compile_ms"]),
        float(row["warmup_ms"]), float(row["kernel_ms"]), float(row["residual_ms"]), ok, row["error"]
    )


def train_bundle(points: Iterable[OpProfilePoint], fitted_overhead_ms: Dict[str, float], activation_factor: Dict[str, float]) -> PredictorBundle:
    grouped = group_points(point for point in points if point.ok)
    if not grouped:
        raise ValueError("no successful profile points; check unsupported.json")
    predictors = {key: train_op_predictor(key, values) for key, values in grouped.items()}
    return PredictorBundle(predictors, fitted_overhead_ms, activation_factor)


def group_points(points: Iterable[OpProfilePoint]) -> Dict[str, List[OpProfilePoint]]:
    grouped: Dict[str, List[OpProfilePoint]] = {}
    for point in points:
        grouped.setdefault(op_key(point.op_name, point.phase, point.dtype), []).append(point)
    return grouped


def train_op_predictor(key: str, points: List[OpProfilePoint]) -> OpPredictor:
    op_name, phase, _ = key.split(":")
    flops = [estimate_flops(point) for point in points]
    kernels = [point.kernel_ms for point in points]
    coeff, intercept = fit_linear(flops, kernels)
    return OpPredictor(op_name, phase, intercept, coeff)


def fit_linear(flops: List[float], kernels: List[float]) -> tuple[float, float]:
    x_mean, y_mean = average(flops), average(kernels)
    variance = sum((value - x_mean) ** 2 for value in flops)
    if variance <= 0.0:
        return 0.0, max(y_mean, 0.0)
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(flops, kernels))
    coeff = covariance / variance
    return max(coeff, 0.0), max(y_mean - coeff * x_mean, 0.0)


def average(values: List[float]) -> float:
    return sum(values) / max(len(values), 1)


def estimate_flops(point: OpProfilePoint) -> float:
    return float(2 * point.m * point.n * point.k)


def predict_ms(bundle: PredictorBundle, op_name: str, phase: str, dtype: str, m: int, n: int, k: int) -> float:
    key = op_key(op_name, phase, dtype)
    predictor = bundle.predictors.get(key)
    if predictor is None:
        raise KeyError(f"missing predictor for {key}; available={len(bundle.predictors)}")
    predicted_ms = predictor.intercept_ms + predictor.flop_coeff_ms * float(2 * m * n * k)
    return max(predicted_ms, 0.0)


def save_bundle(bundle: PredictorBundle, output_path: Path) -> None:
    payload = {
        "predictors": {key: asdict(value) for key, value in bundle.predictors.items()},
        "fitted_overhead_ms": bundle.fitted_overhead_ms,
        "activation_factor": bundle.activation_factor,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_bundle(path: Path) -> PredictorBundle:
    payload = json.loads(path.read_text(encoding="utf-8"))
    predictors = {key: OpPredictor(**value) for key, value in payload["predictors"].items()}
    return PredictorBundle(predictors, payload["fitted_overhead_ms"], payload["activation_factor"])

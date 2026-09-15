import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class HybridCase:
    measured_step_ms: float
    analytical_step_ms: float
    neusight_step_ms: float


@dataclass(frozen=True)
class HybridCalibration:
    best_weight: float
    best_mape_percent: float
    analytical_mape_percent: float
    neusight_mape_percent: float
    blended_step_ms: List[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit hybrid analytical/neusight blend weight from validation rows")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--grid-step", default=0.01, type=float)
    return parser.parse_args()


def load_cases(path: Path) -> List[HybridCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"] if isinstance(payload, dict) and "rows" in payload else payload
    return [to_case(row) for row in rows]


def to_case(row: Dict) -> HybridCase:
    measured = float(row["measured_step_ms"])
    analytical = float(require_any_field(row, ["analytical_step_ms", "predicted_step_ms"]))
    neusight = float(require_field(row, "neusight_step_ms"))
    return HybridCase(measured, analytical, neusight)


def require_field(row: Dict, name: str) -> float:
    if name not in row:
        raise KeyError(f"missing required field {name!r} in calibration row")
    return float(row[name])


def require_any_field(row: Dict, names: List[str]) -> float:
    for name in names:
        if name in row and row[name] is not None:
            return float(row[name])
    joined = ", ".join(repr(name) for name in names)
    raise KeyError(f"missing required field in calibration row; expected one of: {joined}")


def fit_weight(cases: List[HybridCase], grid_step: float) -> HybridCalibration:
    weights = generate_weights(grid_step)
    best = min(weights, key=lambda weight: mape_percent(blended_values(cases, weight), measured_values(cases)))
    best_blended = blended_values(cases, best)
    return HybridCalibration(best, mape_percent(best_blended, measured_values(cases)), mape_percent(analytical_values(cases), measured_values(cases)), mape_percent(neusight_values(cases), measured_values(cases)), best_blended)


def generate_weights(grid_step: float) -> List[float]:
    steps = max(int(round(1.0 / max(grid_step, 1e-6))), 1)
    return [index / steps for index in range(steps + 1)]


def blended_values(cases: Iterable[HybridCase], weight: float) -> List[float]:
    return [(weight * case.analytical_step_ms) + ((1.0 - weight) * case.neusight_step_ms) for case in cases]


def analytical_values(cases: Iterable[HybridCase]) -> List[float]:
    return [case.analytical_step_ms for case in cases]


def neusight_values(cases: Iterable[HybridCase]) -> List[float]:
    return [case.neusight_step_ms for case in cases]


def measured_values(cases: Iterable[HybridCase]) -> List[float]:
    return [case.measured_step_ms for case in cases]


def mape_percent(predicted: List[float], measured: List[float]) -> float:
    errors = [abs(pred - obs) / max(obs, 1e-9) * 100.0 for pred, obs in zip(predicted, measured)]
    return sum(errors) / max(len(errors), 1)


def to_report(cases: List[HybridCase], calibration: HybridCalibration, grid_step: float) -> Dict:
    return {
        "num_cases": len(cases),
        "grid_step": grid_step,
        "best_hybrid_analytical_weight": calibration.best_weight,
        "best_hybrid_mape_percent": calibration.best_mape_percent,
        "analytical_mape_percent": calibration.analytical_mape_percent,
        "neusight_mape_percent": calibration.neusight_mape_percent,
        "recommended_flag": f"--hybrid-analytical-weight {calibration.best_weight:.2f}",
    }


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    cases = load_cases(Path(args.input))
    calibration = fit_weight(cases, args.grid_step)
    report = to_report(cases, calibration, args.grid_step)
    write_json(Path(args.output), report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

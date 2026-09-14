import argparse
import json
from pathlib import Path
from typing import List

from .calibrate import fit_bundle
from .predictors import read_profile_points, save_bundle, train_bundle
from .types import OpProfilePoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA step-time predictors from profile CSV")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dgx-overhead-ms", required=True, type=float)
    parser.add_argument("--radeon-overhead-ms", required=True, type=float)
    parser.add_argument("--activation-factor-off", default=10.0, type=float)
    parser.add_argument("--activation-factor-on", default=4.5, type=float)
    parser.add_argument("--fit-cases", default="")
    parser.add_argument("--fit-report", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    points = load_profile_points(args.profiles)
    overhead = {"dgx_spark_gb10": args.dgx_overhead_ms, "radeon_8060s": args.radeon_overhead_ms}
    factors = {"checkpoint_off": args.activation_factor_off, "checkpoint_on": args.activation_factor_on}
    bundle = train_bundle(points, overhead, factors)
    if args.fit_cases:
        cases = json.loads(Path(args.fit_cases).read_text(encoding="utf-8"))
        bundle, report = fit_bundle(bundle, cases)
        if args.fit_report:
            report_path = Path(args.fit_report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    save_bundle(bundle, Path(args.output))


def load_profile_points(raw_profiles: str) -> List[OpProfilePoint]:
    paths = split_profile_paths(raw_profiles)
    return [point for path in paths for point in read_profile_points(path)]


def split_profile_paths(raw_profiles: str) -> List[Path]:
    paths = [Path(part.strip()) for part in raw_profiles.split(",") if part.strip()]
    if not paths:
        raise ValueError("--profiles must include at least one CSV path")
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing profile CSVs: {', '.join(missing)}")
    return paths


if __name__ == "__main__":
    main()

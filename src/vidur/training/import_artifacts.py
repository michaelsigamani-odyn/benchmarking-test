import argparse
import json
from pathlib import Path

from .artifact_ingest import build_validation_case, collect_points, extract_transfer_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import existing cross-OEM metrics into vidur.training inputs")
    parser.add_argument("--report", required=True)
    parser.add_argument("--model-config", required=True)
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--seq-len", required=True, type=int)
    parser.add_argument("--rank", required=True, type=int)
    parser.add_argument("--alpha", required=True, type=int)
    parser.add_argument("--target-modules", default="q_proj,k_proj,v_proj,o_proj")
    parser.add_argument("--validation-output", required=True)
    parser.add_argument("--transfer-output", required=True)
    return parser.parse_args()


def read_model_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_targets(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    report = Path(args.report)
    model_config = read_model_config(Path(args.model_config))
    points = collect_points(report, args.batch_size, args.seq_len)
    cases = build_validation_case(points, args.rank, args.alpha, parse_targets(args.target_modules), model_config)
    write_json(Path(args.validation_output), cases)
    write_json(Path(args.transfer_output), extract_transfer_metrics(report))


if __name__ == "__main__":
    main()

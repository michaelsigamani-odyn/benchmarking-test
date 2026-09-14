import argparse
import json
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render validation JSON as markdown table")
    parser.add_argument("--validation", required=True)
    parser.add_argument("--transfer", required=False)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_row(row: Dict) -> str:
    step_err = percent_error(row["predicted_step_ms"], row["measured_step_ms"])
    mem_err = percent_error(row["predicted_peak_gb"], row["measured_peak_gb"])
    return f"| {row['device']} | {row['model']} | {row['batch_size']} | {row['sequence_length']} | {row['rank']} | {row['predicted_step_ms']:.2f} | {row['measured_step_ms']:.2f} | {step_err:.2f} | {row['predicted_peak_gb']:.2f} | {row['measured_peak_gb']:.2f} | {mem_err:.2f} |"


def percent_error(predicted: float, measured: float) -> float:
    return abs(predicted - measured) / max(measured, 1e-9) * 100.0


def render_table(rows: List[Dict]) -> str:
    header = "| device | model | batch | seq | rank | predicted step ms | measured step ms | abs err % | predicted peak GB | measured peak GB | abs err % |"
    divider = "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    return "\n".join([header, divider, *[render_row(row) for row in rows]])


def render_metrics(validation: Dict, transfer: Dict | None) -> str:
    parts = [
        f"step_mae_percent={validation['step_mae_percent']:.2f}",
        f"memory_mae_percent={validation['memory_mae_percent']:.2f}",
    ]
    if transfer:
        parts.extend([
            f"iperf3_gbps={transfer['iperf3_bps'] / 1e9:.3f}",
            f"rsync_gbps={transfer['rsync_bps'] / 1e9:.3f}",
            f"mooncake_gbps={transfer['mooncake_bps'] / 1e9:.3f}",
            f"transfer_seconds={transfer['transfer_seconds']:.3f}",
        ])
    return "\n".join(["", "```text", *parts, "```"])


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    validation = load_json(Path(args.validation))
    transfer = load_json(Path(args.transfer)) if args.transfer else None
    markdown = render_table(validation["rows"]) + render_metrics(validation, transfer)
    write_markdown(Path(args.output), markdown)


if __name__ == "__main__":
    main()

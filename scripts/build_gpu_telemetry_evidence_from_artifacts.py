#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_json_block(md: str, heading: str) -> Optional[Any]:
    pattern = re.compile(
        rf"^### {re.escape(heading)}\n\n```json\n(.*?)\n```",
        flags=re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(md)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _extract_source_count(dryrun: str, table_name: str) -> Optional[int]:
    pattern = re.compile(
        rf"TABLE {re.escape(table_name)}\n(?:.|\n)*?SOURCE_COUNT: (\d+)",
        flags=re.MULTILINE,
    )
    m = pattern.search(dryrun)
    if not m:
        return None
    return int(m.group(1))


def _first_row(block: Any) -> Dict[str, Any]:
    if isinstance(block, list) and block:
        row = block[0]
        if isinstance(row, dict):
            return row
    return {}


def build_snapshot(dryrun_path: Path, bq_report_path: Path) -> Dict[str, Any]:
    dryrun = _read_text(dryrun_path)
    bq = _read_text(bq_report_path)

    edge_30d = _first_row(_extract_json_block(bq, "raw_ops.edge_gpu_samples_v1 (last 30 days)"))
    edge_cadence = _first_row(_extract_json_block(bq, "raw_ops.edge_gpu_samples_v1 cadence (last 30 minutes)"))
    edge_state_freshness = _first_row(_extract_json_block(bq, "clean_ops.edge_machine_state_v2 freshness"))
    prod_fact = _first_row(_extract_json_block(bq, "clean_ops.fact_gpu_telemetry_v1 (last 365 days)"))
    prod_fact_1m = _first_row(_extract_json_block(bq, "clean_ops.fact_gpu_telemetry_1m_v1 (last 365 days)"))
    pg_timeliness = _first_row(_extract_json_block(bq, "raw_ops.pg_state_snapshot_v1"))

    snapshot: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_sources": {
            "dryrun_output": str(dryrun_path),
            "bigquery_table_report": str(bq_report_path),
        },
        "authoritative_inventory_counts": {
            "nodes_source_count": _extract_source_count(dryrun, "public.nodes"),
            "gpu_inventory_source_count": _extract_source_count(dryrun, "public.gpu_inventory"),
        },
        "pg_snapshot_timeliness": pg_timeliness,
        "edge_raw_30d": edge_30d,
        "edge_cadence_30m": edge_cadence,
        "edge_machine_state_freshness": edge_state_freshness,
        "prod_fact_gpu_telemetry_365d": prod_fact,
        "prod_fact_gpu_telemetry_1m_365d": prod_fact_1m,
    }
    return snapshot


def _render_markdown(snapshot: Dict[str, Any]) -> str:
    inv = snapshot.get("authoritative_inventory_counts", {})
    edge = snapshot.get("edge_raw_30d", {})
    cadence = snapshot.get("edge_cadence_30m", {})
    freshness = snapshot.get("edge_machine_state_freshness", {})
    prod = snapshot.get("prod_fact_gpu_telemetry_365d", {})
    prod_1m = snapshot.get("prod_fact_gpu_telemetry_1m_365d", {})

    return "\n".join(
        [
            "# GPU telemetry evidence snapshot (artifact-derived)",
            "",
            f"Generated: `{snapshot.get('generated_at_utc')}`",
            "",
            "## Authoritative inventory counts (pg snapshot dry-run)",
            "",
            f"- `public.nodes` source count: **{inv.get('nodes_source_count')}**",
            f"- `public.gpu_inventory` source count: **{inv.get('gpu_inventory_source_count')}**",
            "",
            "## Edge raw telemetry (30d)",
            "",
            f"- total rows: **{edge.get('total_rows')}**",
            f"- distinct hosts: **{edge.get('distinct_hosts')}**",
            f"- distinct host+gpu: **{edge.get('distinct_host_gpu')}**",
            f"- min/max sample ts: `{edge.get('min_ts')}` / `{edge.get('max_ts')}`",
            "",
            "## Edge cadence (30m)",
            "",
            f"- host+gpu with recent samples: **{cadence.get('host_gpu_with_recent_samples')}**",
            f"- median interval seconds: **{cadence.get('median_interval_seconds')}**",
            f"- p90 interval seconds: **{cadence.get('p90_interval_seconds')}**",
            "",
            "## Edge machine freshness summary", 
            "",
            f"- hosts total: **{freshness.get('hosts_total')}**",
            f"- hosts fresh <=30s: **{freshness.get('hosts_fresh_le_30s')}**",
            f"- hosts fresh <=2m: **{freshness.get('hosts_fresh_le_2m')}**",
            f"- max age seconds: **{freshness.get('max_age_s')}**",
            "",
            "## Production fact telemetry status", 
            "",
            f"- `clean_ops.fact_gpu_telemetry_v1` total rows (365d): **{prod.get('total_rows')}**",
            f"- `clean_ops.fact_gpu_telemetry_1m_v1` total rows (365d): **{prod_1m.get('total_rows')}**",
            "",
            "## Notes",
            "",
            "This report is built from existing local evidence artifacts and does not perform live BigQuery/API calls.",
        ]
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build telemetry evidence summary from local artifact files.")
    p.add_argument(
        "--dryrun-output",
        default="/Users/michaelsigamani/odyn-private/dryrun_output.txt",
    )
    p.add_argument(
        "--bq-report",
        default="outputs/bigquery_table_report.md",
    )
    p.add_argument(
        "--out-json",
        default="outputs/gpu_telemetry_evidence_snapshot.json",
    )
    p.add_argument(
        "--out-md",
        default="outputs/gpu_telemetry_evidence_snapshot.md",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = build_snapshot(Path(args.dryrun_output), Path(args.bq_report))

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(_render_markdown(snapshot), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "out_json": str(out_json),
                "out_md": str(out_md),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

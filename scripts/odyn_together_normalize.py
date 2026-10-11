#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from cross_oem_migration.reporting.odyn_together_normalization import (
    TOGETHER_PRICING_URL,
    compute_finetune_effective_cost_per_million,
    compute_finetune_steady_cost_per_million,
    compute_serving_cost_per_million,
    expected_steps,
    extract_fine_tune_pricing_table,
    extract_h100_on_demand_per_gpu_hour,
    fetch_pricing_markdown,
    list_all_fine_tuning_jobs,
    min_charge_binding,
    normalize_job_record,
    now_utc_iso,
    round3,
    run_together_cli_json,
    select_benchmark_jobs,
    token_delta,
    validate_regression_counts,
    write_csv,
    write_json,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Odyn vs Together cost normalization collector."
    )
    parser.add_argument("--workbook", default="", help="Path to Odyn_vs_Together_AI_-_updated.xlsx")
    parser.add_argument("--output-dir", default="outputs/odyn_together", help="Directory for generated files")
    parser.add_argument("--allow-spend", action="store_true", help="Reserved for explicit spend actions (not used by default read-only workflow)")
    parser.add_argument("--job-id", action="append", default=[], help="Optional fine-tuning job IDs to force-include")
    parser.add_argument(
        "--regression-mode",
        choices=["strict", "warn"],
        default="strict",
        help="strict: non-zero exit on regression mismatch; warn: continue but label workbook-only rows.",
    )
    parser.add_argument("--hours-per-month", type=float, default=730.0)
    parser.add_argument("--a100-monthly-usd", type=float, default=10_000.0)
    parser.add_argument("--a100-gpus", type=int, default=8)
    parser.add_argument("--h100-monthly-usd", type=float, default=1_400.0)
    parser.add_argument("--utilisation", type=float, default=1.0)
    parser.add_argument("--latency-target-s", type=float, default=2.0)
    return parser.parse_args()


def _write_methodology(
    output_dir: Path,
    pricing_rows: list[dict[str, Any]],
    h100_price: float | None,
    regression_errors: list[str],
    regression_mode: str,
) -> None:
    checks_block = "\n".join(f"- {e}" for e in regression_errors) if regression_errors else "- none"
    methodology = f"""# METHODOLOGY

Generated: {now_utc_iso()}

## Regression checks
- Mode: {regression_mode}
- Failures:
{checks_block}

## Safety
- Default mode runs only read-only Together CLI commands:
  - `together fine-tuning list --json`
  - `together fine-tuning retrieve <id> --json`
  - `together endpoints list --json`
  - `together endpoints retrieve <id> --json`
  - `together endpoints hardware --json`
- No fine-tune submission, endpoint creation/start, or inference traffic in default mode.

## Together pricing source
- URL: {TOGETHER_PRICING_URL}
- Retrieval timestamp: {now_utc_iso()}

## Fine-tune formulas
- Together effective $/M tokens = `billed_usd / (tokens / 1e6)`
- Together list cost ($) = `(tokens / 1e6) * list_rate_per_million`
- Queue real minutes = `JOB_START - created_at`
- Setup minutes = `TRAINING_START - JOB_START`
- Training phase minutes = `TRAINING_COMPLETE - TRAINING_START`
- Finalise minutes = `JOB_COMPLETE - TRAINING_COMPLETE`
- Wall minutes = `updated_at - created_at`
- Setup+train minutes = `setup + training`
- Expected steps references:
  - `ceil(tokens / (effective_batch_cli * 4096))`
  - `ceil(tokens / (8 * 4096))`

## Together billing units
- Together job `total_price`/`train_price` appears to be nano-USD units.
- Conversion used: `usd = raw_price / 1_000_000_000`.

## Dataset-size mapping note
- `dataset_size` for CLI rows is inferred from token-count buckets (1k/5k/10k).

## Serving formula (reference)
- `$/M = (gpu_hourly_usd / (tokens_per_second * 3600)) * 1e6`
- Utilization-adjusted: `$/M / U`

## Assumptions / unavailable
- Endpoint precision is marked `UNAVAILABLE` unless returned by endpoint metadata.
- H100 on-demand dedicated rate extracted from pricing table: {h100_price if h100_price is not None else 'UNAVAILABLE'}

## Fine-tune pricing rows extracted
- Count: {len(pricing_rows)}
"""
    (output_dir / "METHODOLOGY.md").write_text(methodology, encoding="utf-8")


def _write_claims_check(output_dir: Path, regression_errors: list[str], regression_mode: str, rows: list[dict[str, Any]]) -> None:
    header = "\n".join(["# claims_check", "", "## Regression checks", f"- Mode: {regression_mode}"])
    if regression_errors:
        header += "\n- Failed checks:"
        header += "\n" + "\n".join(f"  - {e}" for e in regression_errors)
    else:
        header += "\n- Failed checks: none"
    excluded = [r for r in rows if r.get("verification") == "CLI_VERIFIED" and r.get("excluded_from_claims")]
    excluded_lines = "\n".join(
        f"- {r.get('job_id')} ({r.get('model')} {r.get('dataset_size')}): {r.get('exclusion_reason')}"
        for r in excluded
    ) or "- none"

    # Downgrade-first policy: claims upgrade only when evidence rows are CLI_VERIFIED and n>=3.
    qwen_verified = [
        r for r in rows
        if r.get("verification") == "CLI_VERIFIED"
        and "qwen" in str(r.get("model", "")).lower()
        and not r.get("excluded_from_claims")
    ]
    qwen_5k_verified = [r for r in qwen_verified if str(r.get("dataset_size")) == "5k"]
    qwen_unverified_present = any(
        r for r in rows
        if "qwen" in str(r.get("model", "")).lower()
        and r.get("verification") != "CLI_VERIFIED"
    )
    # Upgrade only when verified support exists and no unverified dependency remains.
    qwen_turnaround_evidence_ok = (len(qwen_5k_verified) >= 3) and (not qwen_unverified_present)

    claims = """# claims_check

| Claim | Status | Reason |
|---|---|---|
| "$4 per job" and "2.3x to 118x cheaper" | NOT SUPPORTED | Minimum charge is not a per-token list-rate comparison. |
| "First token 2 to 6x sooner" | NEEDS RE-RUN | Together TTFT includes network RTT unless corrected with colocated measurement. |
| "Together sooner only on 27B 10k" | NOT SUPPORTED | Current evidence indicates gpt-oss 5k exceptions as well. |
"""
    claim_safety = """

## Claim safety (auto-generated)
- Policy: claims default to downgraded; upgrade requires CLI_VERIFIED support rows and n >= 3.
- Qwen turnaround claim evidence quality: {qwen_status}
- Excluded jobs from claim ranges:
{excluded_lines}
- Note: claims based on WORKBOOK_UNVERIFIED rows remain downgraded.
""".format(
        qwen_status=("UPGRADE_ELIGIBLE" if qwen_turnaround_evidence_ok else "DOWNGRADED_UNVERIFIED_OR_INSUFFICIENT_N"),
        excluded_lines=excluded_lines,
    )
    claims = claims.replace("# claims_check", header)
    (output_dir / "claims_check.md").write_text(claims + claim_safety, encoding="utf-8")


def _normal_model_name(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    if "/" in s:
        s = s.split("/", 1)[1]
    return s


def _canonical_model_key(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", _normal_model_name(name))


def _parse_dt(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    return round3((end - start).total_seconds() / 60.0)


def _infer_dataset_size_from_tokens(tokens: Any) -> str | None:
    if tokens is None:
        return None
    try:
        t = int(tokens)
    except (TypeError, ValueError):
        return None
    if t in (287_860, 335_328):
        return "1k"
    if t in (1_435_064, 1_672_237):
        return "5k"
    if t in (2_854_762, 3_329_128):
        return "10k"
    return None


def _load_workbook_together_rows(workbook_path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(workbook_path, data_only=False)
    if "Fine-tune data" not in wb.sheetnames:
        return []
    ws = wb["Fine-tune data"]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    name_to_col = {str(h): idx + 1 for idx, h in enumerate(headers) if h}
    required = ["platform", "model", "dataset_size", "steps", "trained_tokens", "train_time_min", "queue_time_min", "total_time_min", "status", "notes"]
    if any(k not in name_to_col for k in required):
        return []

    rows: list[dict[str, Any]] = []
    for r in range(2, ws.max_row + 1):
        platform = ws.cell(r, name_to_col["platform"]).value
        if platform != "Together":
            continue
        rows.append(
            {
                "platform": platform,
                "model": ws.cell(r, name_to_col["model"]).value,
                "dataset_size": ws.cell(r, name_to_col["dataset_size"]).value,
                "steps": ws.cell(r, name_to_col["steps"]).value,
                "trained_tokens": ws.cell(r, name_to_col["trained_tokens"]).value,
                "train_time_min": ws.cell(r, name_to_col["train_time_min"]).value,
                "queue_time_min": ws.cell(r, name_to_col["queue_time_min"]).value,
                "total_time_min": ws.cell(r, name_to_col["total_time_min"]).value,
                "status": ws.cell(r, name_to_col["status"]).value,
                "notes": ws.cell(r, name_to_col["notes"]).value,
            }
        )
    return rows


def _load_workbook_odyn_rows(workbook_path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(workbook_path, data_only=False)
    if "Fine-tune data" not in wb.sheetnames:
        return []
    ws = wb["Fine-tune data"]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    name_to_col = {str(h): idx + 1 for idx, h in enumerate(headers) if h}
    required = ["platform", "model", "dataset_size", "trained_tokens", "total_time_min", "steady_tokens_per_s", "status", "notes"]
    if any(k not in name_to_col for k in required):
        return []

    rows: list[dict[str, Any]] = []
    for r in range(2, ws.max_row + 1):
        platform = ws.cell(r, name_to_col["platform"]).value
        if platform not in ("A100", "H100"):
            continue
        rows.append(
            {
                "platform": platform,
                "model": ws.cell(r, name_to_col["model"]).value,
                "dataset_size": ws.cell(r, name_to_col["dataset_size"]).value,
                "trained_tokens": ws.cell(r, name_to_col["trained_tokens"]).value,
                "total_time_min": ws.cell(r, name_to_col["total_time_min"]).value,
                "steady_tokens_per_s": ws.cell(r, name_to_col["steady_tokens_per_s"]).value,
                "status": ws.cell(r, name_to_col["status"]).value,
                "notes": ws.cell(r, name_to_col["notes"]).value,
            }
        )
    return rows


def _load_inference_rows(workbook_path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(workbook_path, data_only=False)
    if "Inference data" not in wb.sheetnames:
        return []
    ws = wb["Inference data"]
    rows: list[dict[str, Any]] = []
    for r in range(2, ws.max_row + 1):
        model, metric, a100, h100, together, valid = [ws.cell(r, c).value for c in range(1, 7)]
        rows.append({
            "model": model,
            "metric": metric,
            "a100": a100,
            "h100": h100,
            "together": together,
            "valid_runs": valid,
        })
    return rows


def _compute_training_phase_minutes(events: list[dict[str, Any]]) -> float | None:
    start_ts = None
    end_ts = None
    for e in events:
        if e.get("type") == "TRAINING_START":
            start_ts = _parse_dt(e.get("created_at"))
        elif e.get("type") == "TRAINING_COMPLETE":
            end_ts = _parse_dt(e.get("created_at"))
    return _minutes(start_ts, end_ts)


def _event_time(events: list[dict[str, Any]], event_type: str) -> datetime | None:
    for e in events:
        if e.get("type") == event_type:
            return _parse_dt(e.get("created_at"))
    return None


def _event_phase_breakdown(created_at: str | None, finished_at: str | None, events: list[dict[str, Any]]) -> dict[str, Any]:
    created = _parse_dt(created_at)
    finished = _parse_dt(finished_at)
    job_start = _event_time(events, "JOB_START")
    training_start = _event_time(events, "TRAINING_START")
    training_complete = _event_time(events, "TRAINING_COMPLETE")
    job_complete = _event_time(events, "JOB_COMPLETE") or finished

    queue_real = _minutes(created, job_start)
    setup = _minutes(job_start, training_start)
    training = _minutes(training_start, training_complete)
    finalise = _minutes(training_complete, job_complete)
    wall = _minutes(created, finished)
    return {
        "queue_real_min": queue_real,
        "setup_min": setup,
        "training_phase_min": training,
        "finalise_min": finalise,
        "wall_min": wall,
        "setup_plus_training_min": round3((setup or 0) + (training or 0)) if setup is not None and training is not None else None,
    }


def _extract_total_steps_from_events(events: list[dict[str, Any]]) -> int | None:
    for e in events:
        if e.get("type") == "TRAINING_START" and isinstance(e.get("total_steps"), int):
            return int(e["total_steps"])
    for e in reversed(events):
        if e.get("type") == "EPOCH_COMPLETE" and isinstance(e.get("step"), int):
            return int(e["step"])
    return None


def _parse_valid_runs(s: Any) -> tuple[int | None, int | None, int | None]:
    if not isinstance(s, str):
        return None, None, None
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$", s)
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _build_serving_rows(inference_rows: list[dict[str, Any]], a100_rate_hr: float, h100_rate_hr: float, together_h100_rate_hr: float | None, utilisation: float, latency_target_s: float) -> list[dict[str, Any]]:
    throughput: list[dict[str, Any]] = []
    for row in inference_rows:
        model = row.get("model")
        metric = str(row.get("metric") or "")
        mt = re.match(r"Throughput @ (\d+) concurrent \(tok/s\)", metric)
        if not mt:
            continue
        conc = int(mt.group(1))
        if conc not in (16, 32, 64):
            continue
        a100 = row.get("a100")
        h100 = row.get("h100")
        tg = row.get("together")
        if not isinstance(a100, (int, float)) or not isinstance(h100, (int, float)) or not isinstance(tg, (int, float)):
            continue
        va, vh, vt = _parse_valid_runs(row.get("valid_runs"))
        tg_rate = together_h100_rate_hr if together_h100_rate_hr is not None else 5.49
        throughput.append(
            {
                "model": model,
                "concurrency": conc,
                "a100_tps": a100,
                "h100_tps": h100,
                "together_tps": tg,
                "a100_valid_runs": va,
                "h100_valid_runs": vh,
                "together_valid_runs": vt,
                "fewer_than_3_runs_flag": any(v is not None and v < 3 for v in [va, vh, vt]),
                "subset_mismatch_flag": len({v for v in [va, vh, vt] if v is not None}) > 1,
                "together_rate_source": "ASSUMED_1xH100",
                "together_gpu_count": 1,
                "together_precision": "UNAVAILABLE",
                "a100_usd_per_m_output": compute_serving_cost_per_million(float(a100), a100_rate_hr, utilisation),
                "h100_usd_per_m_output": compute_serving_cost_per_million(float(h100), h100_rate_hr, utilisation),
                "together_usd_per_m_output": compute_serving_cost_per_million(float(tg), tg_rate, utilisation),
                "column_scope": "output-only",
                "iso_latency_target_s": latency_target_s,
                "iso_latency_cost_status": "INSUFFICIENT_DATA",
            }
        )
    return throughput


def _build_together_only_high_concurrency_rows(inference_rows: list[dict[str, Any]], together_h100_rate_hr: float | None, utilisation: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rate = together_h100_rate_hr if together_h100_rate_hr is not None else 5.49
    for row in inference_rows:
        metric = str(row.get("metric") or "")
        mt = re.match(r"Throughput @ (\d+) concurrent \(tok/s\)", metric)
        if not mt:
            continue
        conc = int(mt.group(1))
        if conc not in (32, 64):
            continue
        tg = row.get("together")
        if not isinstance(tg, (int, float)):
            continue
        out.append(
            {
                "model": row.get("model"),
                "concurrency": conc,
                "together_tps": tg,
                "together_rate_source": "ASSUMED_1xH100",
                "together_gpu_count": 1,
                "together_precision": "UNAVAILABLE",
                "together_usd_per_m_output": compute_serving_cost_per_million(float(tg), rate, utilisation),
                "column_scope": "output-only",
            }
        )
    return out


def _pricing_map(pricing_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in pricing_rows:
        out[_canonical_model_key(str(row.get("model")))] = row
    return out


def _append_workbook_sheets(
    workbook_path: Path,
    output_dir: Path,
    rows: list[dict[str, Any]],
    serving_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[bool, str]:
    if not workbook_path.exists():
        return False, f"Workbook not found: {workbook_path}"
    workbook_copy = output_dir / f"{workbook_path.stem}_normalised_copy{workbook_path.suffix}"
    shutil.copy2(workbook_path, workbook_copy)
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        return False, f"openpyxl unavailable: {exc}"

    wb = load_workbook(workbook_copy)
    if "Config" in wb.sheetnames:
        del wb["Config"]
    cfg = wb.create_sheet("Config")
    cfg.append(["key", "value", "notes"])
    cfg.append(["hours_per_month", args.hours_per_month, "Global hourly conversion"])
    cfg.append(["a100_monthly_usd", args.a100_monthly_usd, "For 8x A100 basis"])
    cfg.append(["a100_gpus", args.a100_gpus, "A100 count"])
    cfg.append(["h100_monthly_usd", args.h100_monthly_usd, "Single H100 monthly"])
    cfg.append(["utilisation_U", args.utilisation, "Serving utilization divisor"])
    cfg.append(["latency_target_s", args.latency_target_s, "Iso-latency p99 threshold"])

    sheet_name = "Normalised costs"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    headers = [
        "verification",
        "job_id",
        "model",
        "dataset_size",
        "tokens",
        "billed_usd",
        "together_list_rate_usd_per_million",
        "together_min_charge_usd",
        "min_charge_binding",
        "together_effective_usd_per_million",
        "odyn_a100_steady_tokens_per_s",
        "odyn_h100_steady_tokens_per_s",
        "wall_min",
        "odyn_a100_steady_formula_usd_per_million",
        "odyn_h100_steady_formula_usd_per_million",
        "odyn_a100_effective_formula_usd_per_million",
        "odyn_h100_effective_formula_usd_per_million",
        "together_effective_formula_usd_per_million",
    ]
    ws.append(headers)
    for idx, row in enumerate(rows, start=2):
        ws.cell(idx, 1, row.get("verification"))
        ws.cell(idx, 2, row.get("job_id"))
        ws.cell(idx, 3, row.get("model"))
        ws.cell(idx, 4, row.get("dataset_size"))
        ws.cell(idx, 5, row.get("tokens"))
        ws.cell(idx, 6, row.get("billed_usd"))
        ws.cell(idx, 7, row.get("together_list_rate_usd_per_million"))
        ws.cell(idx, 8, row.get("together_min_charge_usd"))
        ws.cell(idx, 9, row.get("min_charge_binding"))
        ws.cell(idx, 10, row.get("together_effective_usd_per_million"))
        ws.cell(idx, 11, row.get("odyn_a100_steady_tokens_per_s"))
        ws.cell(idx, 12, row.get("odyn_h100_steady_tokens_per_s"))
        ws.cell(idx, 13, row.get("wall_min"))
        ws.cell(idx, 14, f"=IF(K{idx}>0,ROUND((Config!$B$3/Config!$B$4/Config!$B$2)/(K{idx}*3600)*1000000,3),\"UNAVAILABLE\")")
        ws.cell(idx, 15, f"=IF(L{idx}>0,ROUND((Config!$B$5/Config!$B$2)/(L{idx}*3600)*1000000,3),\"UNAVAILABLE\")")
        ws.cell(idx, 16, f"=IF(AND(E{idx}>0,M{idx}>0),ROUND((Config!$B$3/Config!$B$4/Config!$B$2)*(M{idx}/60)/(E{idx}/1000000),3),\"UNAVAILABLE\")")
        ws.cell(idx, 17, f"=IF(AND(E{idx}>0,M{idx}>0),ROUND((Config!$B$5/Config!$B$2)*(M{idx}/60)/(E{idx}/1000000),3),\"UNAVAILABLE\")")
        ws.cell(idx, 18, f"=IF(E{idx}>0,ROUND(F{idx}/(E{idx}/1000000),3),\"UNAVAILABLE\")")

    serving_sheet = "Normalised serving"
    if serving_sheet in wb.sheetnames:
        del wb[serving_sheet]
    ws2 = wb.create_sheet(serving_sheet)
    ws2.append([
        "model",
        "concurrency",
        "a100_tps",
        "h100_tps",
        "together_tps",
        "together_rate_source",
        "a100_formula_usd_per_m_output",
        "h100_formula_usd_per_m_output",
        "together_formula_usd_per_m_output",
    ])
    for idx, row in enumerate(serving_rows, start=2):
        ws2.cell(idx, 1, row.get("model"))
        ws2.cell(idx, 2, row.get("concurrency"))
        ws2.cell(idx, 3, row.get("a100_tps"))
        ws2.cell(idx, 4, row.get("h100_tps"))
        ws2.cell(idx, 5, row.get("together_tps"))
        ws2.cell(idx, 6, row.get("together_rate_source"))
        ws2.cell(idx, 7, f"=IF(C{idx}>0,ROUND(((Config!$B$3/Config!$B$4/Config!$B$2)/(C{idx}*3600)*1000000)/Config!$B$6,3),\"UNAVAILABLE\")")
        ws2.cell(idx, 8, f"=IF(D{idx}>0,ROUND(((Config!$B$5/Config!$B$2)/(D{idx}*3600)*1000000)/Config!$B$6,3),\"UNAVAILABLE\")")
        ws2.cell(idx, 9, f"=IF(E{idx}>0,ROUND((5.49/(E{idx}*3600)*1000000)/Config!$B$6,3),\"UNAVAILABLE\")")
    wb.save(workbook_copy)
    return True, str(workbook_copy)


def main() -> int:
    args = _parse_args()
    if args.allow_spend:
        print("--allow-spend provided, but this workflow does not execute any spend actions.", file=sys.stderr)

    if not os.environ.get("TOGETHER_API_KEY") and not os.environ.get("TOGETHERAI_API_KEY"):
        print("Missing Together API key in environment (TOGETHER_API_KEY or TOGETHERAI_API_KEY).", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    jobs, list_pages = list_all_fine_tuning_jobs()
    write_json(
        raw_dir / "fine_tuning_list_pages.json",
        [
            {
                "ok": page.ok,
                "command": page.command,
                "stdout": page.stdout,
                "stderr": page.stderr,
            }
            for page in list_pages
        ],
    )
    if not list_pages or not list_pages[0].ok:
        print("Failed to list fine-tuning jobs; see raw/fine_tuning_list_pages.json", file=sys.stderr)
        return 3

    selected_jobs = select_benchmark_jobs(jobs)

    forced_ids = set(args.job_id or [])
    for job in jobs:
        if job.get("id") in forced_ids and job not in selected_jobs:
            selected_jobs.append(job)

    workbook_together_rows: list[dict[str, Any]] = []
    workbook_odyn_rows: list[dict[str, Any]] = []
    inference_rows: list[dict[str, Any]] = []
    if args.workbook:
        workbook_together_rows = _load_workbook_together_rows(Path(args.workbook))
        workbook_odyn_rows = _load_workbook_odyn_rows(Path(args.workbook))
        inference_rows = _load_inference_rows(Path(args.workbook))

    try:
        markdown = fetch_pricing_markdown()
    except Exception as exc:  # pragma: no cover - network failures are runtime behavior
        markdown = ""
        (raw_dir / "pricing_fetch_error.txt").write_text(str(exc), encoding="utf-8")

    (raw_dir / "together_pricing_page.txt").write_text(markdown, encoding="utf-8")
    pricing_rows = extract_fine_tune_pricing_table(markdown) if markdown else []
    h100_rate = extract_h100_on_demand_per_gpu_hour(markdown) if markdown else None
    pricing_by_model = _pricing_map(pricing_rows)

    a100_rate_hr = args.a100_monthly_usd / args.a100_gpus / args.hours_per_month
    h100_rate_hr = args.h100_monthly_usd / args.hours_per_month

    odyn_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in workbook_odyn_rows:
        key = (_canonical_model_key(str(r.get("model"))), str(r.get("dataset_size") or ""), str(r.get("platform") or ""))
        odyn_map[key] = r

    steady_var_flags: dict[tuple[str, str], bool] = {}
    grouped: dict[tuple[str, str], list[float]] = {}
    for r in workbook_odyn_rows:
        key = (str(r.get("platform") or ""), _canonical_model_key(str(r.get("model"))))
        v = r.get("steady_tokens_per_s")
        if isinstance(v, (int, float)):
            grouped.setdefault(key, []).append(float(v))
    for key, values in grouped.items():
        if len(values) >= 2 and min(values) > 0:
            steady_var_flags[key] = (max(values) / min(values)) > 1.10

    normalized_rows: list[dict[str, Any]] = []
    for job in selected_jobs:
        job_id = job.get("id")
        detail = run_together_cli_json(["fine-tuning", "retrieve", str(job_id)])
        write_json(raw_dir / f"fine_tuning_job_{job_id}.retrieve.meta.json", {
            "ok": detail.ok,
            "command": detail.command,
            "stdout": detail.stdout,
            "stderr": detail.stderr,
        })
        (raw_dir / f"fine_tuning_job_{job_id}.retrieve.raw.json").write_text(detail.stdout, encoding="utf-8")
        events_result = run_together_cli_json(["fine-tuning", "list-events", str(job_id)])
        write_json(raw_dir / f"fine_tuning_job_{job_id}.events.meta.json", {
            "ok": events_result.ok,
            "command": events_result.command,
            "stdout": events_result.stdout,
            "stderr": events_result.stderr,
        })
        (raw_dir / f"fine_tuning_job_{job_id}.events.raw.json").write_text(events_result.stdout, encoding="utf-8")

        payload = detail.json_value if detail.ok else job
        events_payload = events_result.json_value if (events_result.ok and isinstance(events_result.json_value, list)) else []
        row = normalize_job_record(payload)
        phases = _event_phase_breakdown(payload.get("created_at"), payload.get("updated_at"), events_payload)

        training_type = payload.get("training_type") or {}
        batch_cli = payload.get("batch_size")
        grad_acc = payload.get("gradient_accumulation_steps")
        eff_batch_cli = (batch_cli * grad_acc) if isinstance(batch_cli, int) and isinstance(grad_acc, int) else None
        observed_steps = _extract_total_steps_from_events(events_payload)
        expected_eff_cli = expected_steps(row.get("tokens"), eff_batch_cli, 4096)
        expected_eff8 = expected_steps(row.get("tokens"), 8, 4096)
        post_queue_min = row.get("wall_min") - row.get("queue_min") if isinstance(row.get("wall_min"), (int, float)) and isinstance(row.get("queue_min"), (int, float)) else None

        row["verification"] = "CLI_VERIFIED" if detail.ok else "UNAVAILABLE"
        row["dataset_size"] = _infer_dataset_size_from_tokens(row.get("tokens"))
        row["model"] = payload.get("model")
        row["model_normalized"] = _normal_model_name(str(payload.get("model")))
        row["status"] = payload.get("status")
        row["max_seq_length"] = payload.get("max_seq_length")
        row["packing"] = payload.get("packing")
        row["steps_paid_for"] = payload.get("steps_paid_for")
        row["steps_reported"] = observed_steps
        row["steps"] = observed_steps if observed_steps is not None else "UNAVAILABLE"
        row["batch_size_cli"] = batch_cli
        row["gradient_accumulation_steps_cli"] = grad_acc
        row["effective_batch_cli"] = eff_batch_cli
        row["expected_steps_at_cli_effective_batch"] = expected_eff_cli
        row["expected_steps_at_effective_batch_8"] = expected_eff8
        row["steps_far_from_expected"] = (
            abs(observed_steps - expected_eff_cli) > max(2, int(expected_eff_cli * 0.2))
            if (observed_steps is not None and expected_eff_cli is not None)
            else "UNAVAILABLE"
        )
        row["queue_real_min"] = phases.get("queue_real_min")
        row["setup_min"] = phases.get("setup_min")
        row["training_phase_min"] = phases.get("training_phase_min")
        row["finalise_min"] = phases.get("finalise_min")
        row["wall_min"] = phases.get("wall_min") or row.get("wall_min")
        row["setup_plus_training_min"] = phases.get("setup_plus_training_min")
        row["queue_plus_setup_min"] = (
            round3((phases.get("queue_real_min") or 0) + (phases.get("setup_min") or 0))
            if phases.get("queue_real_min") is not None and phases.get("setup_min") is not None
            else "UNAVAILABLE"
        )
        # Rename queue_min to real queue for CLI-verified rows.
        row["queue_min"] = phases.get("queue_real_min") if phases.get("queue_real_min") is not None else row.get("queue_min")
        row["post_queue_min"] = (
            round3((row.get("wall_min") - row.get("queue_min")))
            if isinstance(row.get("wall_min"), (int, float)) and isinstance(row.get("queue_min"), (int, float))
            else round3(post_queue_min)
        )
        row["lora_target_mismatch_all_linear"] = (
            str(training_type.get("lora_trainable_modules") or "") != "all-linear"
        )
        row["billed_usd_source"] = "job.total_price"
        row.pop("training_min", None)
        row.pop("expected_steps_at_4096", None)

        exclusion_reasons: list[str] = []
        if isinstance(row.get("max_seq_length"), int) and row.get("max_seq_length") != 4096:
            exclusion_reasons.append(f"different max_seq_length ({row.get('max_seq_length')})")
        # 1k step-floor pattern: reported steps materially above expected-at-batch8.
        if str(row.get("dataset_size")) == "1k" and isinstance(row.get("steps_reported"), int) and isinstance(row.get("expected_steps_at_effective_batch_8"), int):
            if row["steps_reported"] >= int(math.ceil(row["expected_steps_at_effective_batch_8"] * 1.8)):
                exclusion_reasons.append("1k step-floor pattern (steps far above expected-at-batch8)")
        row["excluded_from_claims"] = bool(exclusion_reasons)
        row["exclusion_reason"] = "; ".join(exclusion_reasons) if exclusion_reasons else ""

        model_key = _canonical_model_key(str(row.get("model")))
        price_row = pricing_by_model.get(model_key, {})
        list_rate = price_row.get("lora_sft_usd_per_million")
        min_charge = price_row.get("minimum_charge_usd")
        row["together_list_rate_usd_per_million"] = list_rate
        row["together_min_charge_usd"] = min_charge
        row["min_charge_binding"] = min_charge_binding(row.get("tokens"), list_rate, min_charge)
        row["together_list_cost_usd"] = (
            round3((row.get("tokens") / 1_000_000.0) * list_rate)
            if isinstance(row.get("tokens"), int) and isinstance(list_rate, (int, float))
            else None
        )
        row["break_even_tokens_for_min_charge"] = (
            int(math.ceil(min_charge / list_rate * 1_000_000.0))
            if isinstance(list_rate, (int, float)) and isinstance(min_charge, (int, float)) and list_rate > 0
            else None
        )

        ds = str(row.get("dataset_size") or "")
        for platform, rate_hr in [("A100", a100_rate_hr), ("H100", h100_rate_hr)]:
            o = odyn_map.get((model_key, ds, platform))
            steady_tps = o.get("steady_tokens_per_s") if o else None
            odyn_wall = o.get("total_time_min") if o else None
            odyn_trained = o.get("trained_tokens") if o else None
            row[f"odyn_{platform.lower()}_steady_tokens_per_s"] = steady_tps
            row[f"odyn_{platform.lower()}_steady_usd_per_million"] = compute_finetune_steady_cost_per_million(rate_hr, steady_tps)
            row[f"odyn_{platform.lower()}_effective_usd_per_million"] = compute_finetune_effective_cost_per_million(rate_hr, odyn_wall, row.get("tokens"))
            row[f"odyn_{platform.lower()}_trained_tokens"] = odyn_trained
            row[f"odyn_{platform.lower()}_token_delta_vs_together"] = token_delta(row.get("tokens"), odyn_trained)
            row[f"odyn_{platform.lower()}_trained_less_than_dataset"] = (
                (odyn_trained is not None and row.get("tokens") is not None and odyn_trained < row.get("tokens"))
                if (isinstance(odyn_trained, int) and isinstance(row.get("tokens"), int))
                else "UNAVAILABLE"
            )
            row[f"odyn_{platform.lower()}_steady_variation_gt10pct"] = steady_var_flags.get((platform, model_key), "UNAVAILABLE")
            if list_rate is not None and row.get(f"odyn_{platform.lower()}_steady_usd_per_million"):
                row[f"ratio_together_list_to_odyn_{platform.lower()}_steady"] = list_rate / row[f"odyn_{platform.lower()}_steady_usd_per_million"]
            if list_rate is not None and row.get(f"odyn_{platform.lower()}_effective_usd_per_million"):
                row[f"ratio_together_list_to_odyn_{platform.lower()}_effective"] = list_rate / row[f"odyn_{platform.lower()}_effective_usd_per_million"]

        normalized_rows.append(row)

    cli_keyed = {
        (_normal_model_name(str(r.get("model"))), str(r.get("dataset_size") or "")): r
        for r in normalized_rows
        if r.get("dataset_size")
    }
    if args.regression_mode == "warn" and workbook_together_rows:
        for w in workbook_together_rows:
            key = (_normal_model_name(str(w.get("model"))), str(w.get("dataset_size") or ""))
            if key in cli_keyed:
                continue
            normalized_rows.append(
                {
                    "verification": "WORKBOOK_UNVERIFIED",
                    "job_id": "UNAVAILABLE",
                    "model": w.get("model"),
                    "model_normalized": _normal_model_name(str(w.get("model"))),
                    "dataset_size": w.get("dataset_size"),
                    "status": "UNAVAILABLE",
                    "workbook_status": w.get("status"),
                    "steps": w.get("steps"),
                    "steps_reported": w.get("steps"),
                    "tokens": w.get("trained_tokens"),
                    "queue_min": w.get("queue_time_min"),
                    "queue_real_min": "UNAVAILABLE",
                    "setup_min": "UNAVAILABLE",
                    "post_queue_min": w.get("train_time_min"),
                    "training_phase_min": "UNAVAILABLE",
                    "finalise_min": "UNAVAILABLE",
                    "setup_plus_training_min": "UNAVAILABLE",
                    "wall_min": w.get("total_time_min"),
                    "billed_usd": None,
                    "billed_usd_source": "UNAVAILABLE",
                    "max_seq_length": "UNAVAILABLE",
                    "packing": "UNAVAILABLE",
                    "steps_paid_for": "UNAVAILABLE",
                    "together_effective_usd_per_million": None,
                    "together_list_rate_usd_per_million": pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million"),
                    "together_min_charge_usd": pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("minimum_charge_usd"),
                    "together_list_cost_usd": (
                        round3((w.get("trained_tokens") / 1_000_000.0) * pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million"))
                        if isinstance(w.get("trained_tokens"), int) and isinstance(pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million"), (int, float))
                        else None
                    ),
                    "break_even_tokens_for_min_charge": (
                        int(math.ceil(
                            pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("minimum_charge_usd")
                            / pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million")
                            * 1_000_000.0
                        ))
                        if isinstance(pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("minimum_charge_usd"), (int, float))
                        and isinstance(pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million"), (int, float))
                        and pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million") > 0
                        else None
                    ),
                    "min_charge_binding": min_charge_binding(
                        w.get("trained_tokens"),
                        pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("lora_sft_usd_per_million"),
                        pricing_by_model.get(_canonical_model_key(str(w.get("model"))), {}).get("minimum_charge_usd"),
                    ),
                    "notes": f"WORKBOOK_STATUS={w.get('status')}; {w.get('notes') or ''}",
                    "excluded_from_claims": True,
                    "exclusion_reason": "WORKBOOK_UNVERIFIED",
                }
            )

    # Add Odyn normalization columns for workbook-unverified rows too.
    for row in normalized_rows:
        model_key = _canonical_model_key(str(row.get("model")))
        ds = str(row.get("dataset_size") or "")
        list_rate = row.get("together_list_rate_usd_per_million")
        if list_rate is None:
            list_rate = pricing_by_model.get(model_key, {}).get("lora_sft_usd_per_million")
            row["together_list_rate_usd_per_million"] = list_rate
        for platform, rate_hr in [("A100", a100_rate_hr), ("H100", h100_rate_hr)]:
            ksteady = f"odyn_{platform.lower()}_steady_tokens_per_s"
            if ksteady in row:
                continue
            o = odyn_map.get((model_key, ds, platform))
            steady_tps = o.get("steady_tokens_per_s") if o else None
            odyn_wall = o.get("total_time_min") if o else None
            odyn_trained = o.get("trained_tokens") if o else None
            row[ksteady] = steady_tps
            row[f"odyn_{platform.lower()}_steady_usd_per_million"] = compute_finetune_steady_cost_per_million(rate_hr, steady_tps)
            row[f"odyn_{platform.lower()}_effective_usd_per_million"] = compute_finetune_effective_cost_per_million(rate_hr, odyn_wall, row.get("tokens"))
            row[f"odyn_{platform.lower()}_trained_tokens"] = odyn_trained
            row[f"odyn_{platform.lower()}_token_delta_vs_together"] = token_delta(row.get("tokens"), odyn_trained)
            row[f"odyn_{platform.lower()}_trained_less_than_dataset"] = (
                (odyn_trained is not None and row.get("tokens") is not None and odyn_trained < row.get("tokens"))
                if (isinstance(odyn_trained, int) and isinstance(row.get("tokens"), int))
                else "UNAVAILABLE"
            )
            row[f"odyn_{platform.lower()}_steady_variation_gt10pct"] = steady_var_flags.get((platform, model_key), "UNAVAILABLE")
            if list_rate is not None and row.get(f"odyn_{platform.lower()}_steady_usd_per_million"):
                row[f"ratio_together_list_to_odyn_{platform.lower()}_steady"] = list_rate / row[f"odyn_{platform.lower()}_steady_usd_per_million"]
            if list_rate is not None and row.get(f"odyn_{platform.lower()}_effective_usd_per_million"):
                row[f"ratio_together_list_to_odyn_{platform.lower()}_effective"] = list_rate / row[f"odyn_{platform.lower()}_effective_usd_per_million"]

    # Missing Qwen dashboard IDs needed to verify workbook claims.
    if workbook_together_rows:
        needed: list[str] = []
        for w in workbook_together_rows:
            if "qwen" not in str(w.get("model", "")).lower():
                continue
            key = (_normal_model_name(str(w.get("model"))), str(w.get("dataset_size") or ""))
            if key not in cli_keyed:
                needed.append(f"{w.get('model')} {w.get('dataset_size')} (expected tokens={w.get('trained_tokens')})")
        (output_dir / "missing_qwen_job_ids_needed.txt").write_text("\n".join(needed), encoding="utf-8")

    # Batch/grad summary for quick audit.
    batch_rows = [
        {
            "job_id": r.get("job_id"),
            "model": r.get("model"),
            "batch_size_cli": r.get("batch_size_cli"),
            "gradient_accumulation_steps_cli": r.get("gradient_accumulation_steps_cli"),
            "effective_batch_cli": r.get("effective_batch_cli"),
        }
        for r in normalized_rows
        if r.get("verification") == "CLI_VERIFIED"
    ]
    write_csv(output_dir / "together_batch_grad_fields.csv", batch_rows)

    # Focus inspection row requested for long 9B job.
    inspect_job_id = "ft-bcf4ff51-89fc"
    inspect_row = next((r for r in normalized_rows if r.get("job_id") == inspect_job_id), None)
    if inspect_row:
        inspect_payload = {
            "job_id": inspect_job_id,
            "model": inspect_row.get("model"),
            "batch_size_cli": inspect_row.get("batch_size_cli"),
            "gradient_accumulation_steps_cli": inspect_row.get("gradient_accumulation_steps_cli"),
            "effective_batch_cli": inspect_row.get("effective_batch_cli"),
            "steps_reported": inspect_row.get("steps_reported"),
            "expected_steps_at_cli_effective_batch": inspect_row.get("expected_steps_at_cli_effective_batch"),
            "packing": "See raw retrieve JSON",
            "max_seq_length": "See raw retrieve JSON",
            "steps_paid_for": "See raw retrieve JSON",
        }
        write_json(output_dir / "inspect_ft-bcf4ff51-89fc.json", inspect_payload)

    regression_errors = validate_regression_counts([r for r in normalized_rows if r.get("verification") == "CLI_VERIFIED"])

    write_csv(output_dir / "normalised_finetune.csv", normalized_rows)
    serving_rows = _build_serving_rows(inference_rows, a100_rate_hr, h100_rate_hr, h100_rate, args.utilisation, args.latency_target_s)
    write_csv(output_dir / "normalised_serving.csv", serving_rows)
    together_only_rows = _build_together_only_high_concurrency_rows(inference_rows, h100_rate, args.utilisation)
    write_csv(output_dir / "normalised_serving_together_only.csv", together_only_rows)
    write_json(output_dir / "together_finetune_pricing.json", {
        "source_url": TOGETHER_PRICING_URL,
        "retrieved_at": now_utc_iso(),
        "rows": pricing_rows,
        "h100_on_demand_usd_per_gpu_hr": h100_rate,
    })
    _write_methodology(output_dir, pricing_rows, h100_rate, regression_errors, args.regression_mode)
    _write_claims_check(output_dir, regression_errors, args.regression_mode, normalized_rows)

    if args.workbook:
        ok, info = _append_workbook_sheets(Path(args.workbook), output_dir, normalized_rows, serving_rows, args)
        if ok:
            (output_dir / "workbook_output.txt").write_text(info, encoding="utf-8")
        else:
            (output_dir / "workbook_output.txt").write_text(f"UNAVAILABLE: {info}", encoding="utf-8")

    if regression_errors:
        (output_dir / "regression_errors.txt").write_text("\n".join(regression_errors), encoding="utf-8")
        print("Regression token-count check failed; see regression_errors.txt", file=sys.stderr)
        if args.regression_mode == "strict":
            return 4

    print(f"Wrote outputs to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

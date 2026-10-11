#!/usr/bin/env python3
"""Build curated Tableau-native authoring assets for the CEO dashboard rebuild.

This script uses only the packaged snapshot CSVs under ../data and emits
semantically separated datasets that avoid unit-mixing and false-zero handling.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data"
OUT = Path(__file__).resolve().parent


def _read_csv(name: str) -> List[Dict[str, str]]:
    path = SRC / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def _to_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_bool(v: Optional[str]) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s == "":
        return None
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _safe_pct(num: float, den: float) -> Optional[float]:
    if den == 0:
        return None
    return (num / den) * 100.0


def _fmt_pct(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}%"


def _fmt_num(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "N/A"
    if float(v).is_integer():
        return f"{int(v)}"
    return f"{v:.{digits}f}"


def _max_ts(rows: Iterable[Dict[str, str]], field: str) -> Optional[str]:
    vals = [r.get(field, "") for r in rows if r.get(field, "")]
    if not vals:
        return None
    return max(vals)


def _p95(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(math.ceil(0.95 * len(ordered))) - 1
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
    if total <= 0:
        return None, None
    p = successes / total
    denom = 1 + (z * z) / total
    centre = p + (z * z) / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + (z * z) / (4 * total)) / total)
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return lo * 100, hi * 100


def main() -> None:
    runtime_rows = _read_csv("tableau_ceo_digester_runtime_accuracy_v1.csv")
    pricing_rows = _read_csv("tableau_ceo_digester_pricing_accuracy_v1.csv")
    vram_rows = _read_csv("tableau_ceo_digester_vram_accuracy_v1.csv")
    eval_rows = _read_csv("tableau_ceo_digester_evaluations_v1.csv")
    util_rows = _read_csv("tableau_ceo_gpu_utilization_v1.csv")
    concurrency_rows = _read_csv("tableau_ceo_concurrency_v1.csv")
    commercial_rows = _read_csv("tableau_ceo_commercial_benchmark_v1.csv")
    fleet_summary_rows = _read_csv("tableau_ceo_fleet_summary_v1.csv")
    fleet_overview_rows = _read_csv("tableau_ceo_fleet_machine_overview_v1.csv")
    fleet_detail_rows = _read_csv("tableau_ceo_fleet_machine_detail_v1.csv")
    compute_div_rows = _read_csv("tableau_ceo_compute_diversity_v1.csv")
    scheduler_rows = _read_csv("tableau_ceo_scheduler_economics_v1.csv")
    job_rows = _read_csv("tableau_ceo_job_investigation_v1.csv")
    freshness_rows = _read_csv("tableau_ceo_data_freshness_v1.csv")

    # Cohorts
    runtime_matched = [r for r in runtime_rows if r.get("match_status") == "matched_to_job"]
    runtime_completed = [r for r in runtime_matched if r.get("job_status") == "completed"]
    runtime_completed_with_actual = [
        r
        for r in runtime_completed
        if _to_float(r.get("predicted_runtime_hours")) is not None
        and _to_float(r.get("actual_runtime_hours")) is not None
        and not _to_bool(r.get("missing_actual_runtime"))
    ]

    pricing_matched = [r for r in pricing_rows if r.get("match_status") == "matched_to_job"]
    pricing_completed = [r for r in pricing_matched if r.get("job_status") == "completed"]
    pricing_completed_with_actual = [
        r
        for r in pricing_completed
        if _to_float(r.get("estimated_total_cost_usd")) is not None
        and _to_float(r.get("actual_operational_cost_usd")) is not None
        and not _to_bool(r.get("missing_actual_cost"))
    ]

    runtime_mape_pct = mean(
        [_to_float(r.get("runtime_abs_pct_error")) for r in runtime_completed_with_actual if _to_float(r.get("runtime_abs_pct_error")) is not None]
    ) * 100
    runtime_under_successes = sum(1 for r in runtime_completed_with_actual if _to_bool(r.get("runtime_underestimate_flag")) is True)
    runtime_under_pct = _safe_pct(runtime_under_successes, len(runtime_completed_with_actual))
    runtime_under_ci_lo, runtime_under_ci_hi = _wilson_interval(runtime_under_successes, len(runtime_completed_with_actual))

    cost_mape_pct = mean(
        [_to_float(r.get("cost_abs_pct_error")) for r in pricing_completed_with_actual if _to_float(r.get("cost_abs_pct_error")) is not None]
    ) * 100
    cost_under_successes = sum(1 for r in pricing_completed_with_actual if _to_bool(r.get("cost_underestimate_flag")) is True)
    cost_under_pct = _safe_pct(cost_under_successes, len(pricing_completed_with_actual))
    cost_under_ci_lo, cost_under_ci_hi = _wilson_interval(cost_under_successes, len(pricing_completed_with_actual))

    workload_success_pct = _safe_pct(len(runtime_completed), len(runtime_matched))
    failed_or_stopped = [r for r in runtime_matched if r.get("job_status") in {"failed", "stopped"}]
    oom_failures = [r for r in failed_or_stopped if _to_bool(r.get("is_oom_failure")) is True]

    # Utilisation timeseries from machine detail (raw telemetry)
    util_by_ts: Dict[str, Dict[str, float]] = {}
    for r in fleet_detail_rows:
        ts = r.get("sample_ts", "")
        if not ts:
            continue
        bucket = util_by_ts.setdefault(ts, {"sample_rows": 0.0, "util_rows": 0.0, "util_sum": 0.0})
        bucket["sample_rows"] += 1
        util = _to_float(r.get("util_gpu_pct"))
        if util is not None:
            bucket["util_rows"] += 1
            bucket["util_sum"] += util

    util_ts_rows: List[Dict[str, object]] = []
    for ts in sorted(util_by_ts):
        b = util_by_ts[ts]
        avg_util = (b["util_sum"] / b["util_rows"]) if b["util_rows"] else None
        cov = _safe_pct(b["util_rows"], b["sample_rows"])
        util_ts_rows.append(
            {
                "sample_ts": ts,
                "sample_date": ts.split(" ")[0],
                "sample_rows": int(b["sample_rows"]),
                "util_rows": int(b["util_rows"]),
                "util_coverage_pct": cov,
                "avg_gpu_utilization_pct": avg_util,
                "reference_line_pct": 50.0,
                "plane": "edge",
                "note": "Computed from machine-level telemetry rows where util_gpu_pct is present.",
            }
        )

    avg_gpu_util = None
    if util_ts_rows:
        vals = [r["avg_gpu_utilization_pct"] for r in util_ts_rows if r["avg_gpu_utilization_pct"] is not None]
        avg_gpu_util = mean(vals) if vals else None

    # Concurrency timeline (already event-level)
    conc_rows = []
    for r in sorted(concurrency_rows, key=lambda x: x.get("ts", "")):
        conc_rows.append(
            {
                "ts": r.get("ts", ""),
                "metric_date": r.get("metric_date", ""),
                "concurrent_gpu_jobs": _to_float(r.get("concurrent_gpu_jobs")),
                "concurrent_users": _to_float(r.get("concurrent_users")),
            }
        )
    peak_gpu_jobs = max([_to_float(r.get("concurrent_gpu_jobs")) or 0 for r in concurrency_rows], default=None)
    peak_users = max([_to_float(r.get("concurrent_users")) or 0 for r in concurrency_rows], default=None)

    # Workload outcomes by week from matched runtime cohort
    outcomes_by_week: Dict[str, Counter] = defaultdict(Counter)
    for r in runtime_matched:
        wk = r.get("prediction_year_week") or "unknown"
        st = r.get("job_status") or "unknown"
        outcomes_by_week[wk][st] += 1
    outcome_rows: List[Dict[str, object]] = []
    for wk in sorted(outcomes_by_week):
        c = outcomes_by_week[wk]
        total = sum(c.values())
        completed = c.get("completed", 0)
        failed = c.get("failed", 0)
        stopped = c.get("stopped", 0)
        unknown = c.get("unknown", 0)
        outcome_rows.append(
            {
                "year_week": wk,
                "completed_jobs": completed,
                "failed_jobs": failed,
                "stopped_jobs": stopped,
                "unknown_jobs": unknown,
                "total_jobs": total,
                "success_rate_pct": _safe_pct(completed, total),
                "failure_or_stop_rate_pct": _safe_pct(failed + stopped, total),
            }
        )

    # OOM breakdown among failed/stopped matched jobs
    oom_by_week: Dict[str, Counter] = defaultdict(Counter)
    for r in failed_or_stopped:
        wk = r.get("prediction_year_week") or "unknown"
        is_oom = _to_bool(r.get("is_oom_failure"))
        bucket = "OOM" if is_oom is True else ("NON_OOM" if is_oom is False else "UNKNOWN")
        oom_by_week[wk][bucket] += 1

    oom_rows: List[Dict[str, object]] = []
    for wk in sorted(oom_by_week):
        c = oom_by_week[wk]
        total = sum(c.values())
        for bucket in ["OOM", "NON_OOM", "UNKNOWN"]:
            n = c.get(bucket, 0)
            if n == 0:
                continue
            oom_rows.append(
                {
                    "year_week": wk,
                    "failure_bucket": bucket,
                    "jobs": n,
                    "share_of_failures_pct": _safe_pct(n, total),
                    "total_failed_or_stopped_jobs": total,
                }
            )

    # Commercial comparability by model/workload
    key_rows: Dict[Tuple[str, str], Dict[str, object]] = {}
    for r in commercial_rows:
        key = (r.get("workload_type", ""), r.get("model_id", ""))
        rec = key_rows.setdefault(
            key,
            {
                "workload_type": key[0],
                "model_id": key[1],
                "odyn_rows": 0,
                "together_rows": 0,
                "odyn_cost_rows": 0,
                "together_cost_rows": 0,
                "comparison_supported": "false",
                "status": "UNAVAILABLE",
                "na_reason": "",
            },
        )
        provider = (r.get("provider") or "").lower()
        cost = _to_float(r.get("cost_per_million_tokens_usd"))
        if provider == "odyn":
            rec["odyn_rows"] += 1
            if cost is not None:
                rec["odyn_cost_rows"] += 1
        elif provider == "together":
            rec["together_rows"] += 1
            if cost is not None:
                rec["together_cost_rows"] += 1

    commercial_comp_rows: List[Dict[str, object]] = []
    for _, rec in sorted(key_rows.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        supported = (
            rec["odyn_rows"] > 0
            and rec["together_rows"] > 0
            and rec["odyn_cost_rows"] > 0
            and rec["together_cost_rows"] > 0
        )
        rec["comparison_supported"] = "true" if supported else "false"
        rec["status"] = "MEASURED" if supported else "UNAVAILABLE"
        rec["na_reason"] = (
            "Missing governed token_count + governed buyer/supplier pricing table join in current BigQuery schema."
            if not supported
            else ""
        )
        commercial_comp_rows.append(rec)

    # Digester quality availability cards
    observed_vram = [r for r in vram_rows if _to_float(r.get("observed_peak_vram_gb")) is not None]
    digester_availability_rows = [
        {
            "metric": "VRAM prediction accuracy (MAPE)",
            "status": "UNAVAILABLE",
            "coverage_n": len(observed_vram),
            "coverage_denominator": len(vram_rows),
            "coverage_pct": _safe_pct(len(observed_vram), len(vram_rows)),
            "value": "N/A",
            "unit": "%",
            "explanation": "Observed VRAM exists for only 7/83 rows; coverage is too low for executive KPI use.",
        },
        {
            "metric": "LangSmith hallucination evaluation",
            "status": "UNAVAILABLE",
            "coverage_n": len(eval_rows),
            "coverage_denominator": len(runtime_rows),
            "coverage_pct": _safe_pct(len(eval_rows), len(runtime_rows)),
            "value": "N/A",
            "unit": "score",
            "explanation": "No governed LangSmith evaluation records in snapshot extract.",
        },
    ]

    # Estimation accuracy summary cards
    estimation_summary_rows = [
        {
            "metric": "Runtime MAPE",
            "value_pct": runtime_mape_pct,
            "sample_size_n": len(runtime_completed_with_actual),
            "denominator_note": "Completed matched jobs with predicted+actual runtime",
            "status": "MEASURED",
            "ci_low_pct": "",
            "ci_high_pct": "",
            "value_display": _fmt_pct(runtime_mape_pct),
        },
        {
            "metric": "Cost MAPE",
            "value_pct": cost_mape_pct,
            "sample_size_n": len(pricing_completed_with_actual),
            "denominator_note": "Completed matched jobs with estimated+actual cost",
            "status": "MEASURED",
            "ci_low_pct": "",
            "ci_high_pct": "",
            "value_display": _fmt_pct(cost_mape_pct),
        },
        {
            "metric": "Runtime underestimation rate",
            "value_pct": runtime_under_pct,
            "sample_size_n": len(runtime_completed_with_actual),
            "denominator_note": "Completed matched jobs with predicted+actual runtime",
            "status": "MEASURED",
            "ci_low_pct": runtime_under_ci_lo,
            "ci_high_pct": runtime_under_ci_hi,
            "value_display": _fmt_pct(runtime_under_pct),
        },
        {
            "metric": "Cost underestimation rate",
            "value_pct": cost_under_pct,
            "sample_size_n": len(pricing_completed_with_actual),
            "denominator_note": "Completed matched jobs with estimated+actual cost",
            "status": "MEASURED",
            "ci_low_pct": cost_under_ci_lo,
            "ci_high_pct": cost_under_ci_hi,
            "value_display": _fmt_pct(cost_under_pct),
        },
    ]

    runtime_scatter_rows = []
    for r in runtime_completed_with_actual:
        runtime_scatter_rows.append(
            {
                "workload_id": r.get("workload_id", ""),
                "job_id": r.get("job_id", ""),
                "prediction_date": r.get("prediction_date", ""),
                "prediction_year_week": r.get("prediction_year_week", ""),
                "model_id": r.get("predicted_model_id", ""),
                "predicted_runtime_hours": _to_float(r.get("predicted_runtime_hours")),
                "actual_runtime_hours": _to_float(r.get("actual_runtime_hours")),
                "runtime_abs_pct_error": _to_float(r.get("runtime_abs_pct_error")),
                "runtime_underestimate_flag": r.get("runtime_underestimate_flag", ""),
                "selected_gpu_tier": r.get("selected_gpu_tier", ""),
                "selected_gpu_count": r.get("selected_gpu_count", ""),
            }
        )

    cost_scatter_rows = []
    for r in pricing_completed_with_actual:
        cost_scatter_rows.append(
            {
                "workload_id": r.get("workload_id", ""),
                "job_id": r.get("job_id", ""),
                "prediction_date": r.get("prediction_date", ""),
                "prediction_year_week": r.get("prediction_year_week", ""),
                "model_id": r.get("predicted_model_id", ""),
                "estimated_total_cost_usd": _to_float(r.get("estimated_total_cost_usd")),
                "actual_operational_cost_usd": _to_float(r.get("actual_operational_cost_usd")),
                "cost_abs_pct_error": _to_float(r.get("cost_abs_pct_error")),
                "cost_underestimate_flag": r.get("cost_underestimate_flag", ""),
                "selected_gpu_tier": r.get("selected_gpu_tier", ""),
                "selected_gpu_count": r.get("selected_gpu_count", ""),
            }
        )

    # Fleet health + diversity
    fleet_overview_rows_out = []
    for r in sorted(fleet_overview_rows, key=lambda x: x.get("host", "")):
        fleet_overview_rows_out.append(
            {
                "host": r.get("host", ""),
                "display_name": r.get("display_name", ""),
                "vendor": r.get("vendor", ""),
                "state": r.get("state", ""),
                "machine_health_state": r.get("machine_health_state", ""),
                "telemetry_status": r.get("telemetry_status", ""),
                "telemetry_fresh": r.get("telemetry_fresh", ""),
                "last_sample_ts": r.get("last_sample_ts", ""),
                "age_s": _to_float(r.get("age_s")),
                "expected_gpus": _to_float(r.get("expected_gpus")),
                "gpu_rows": _to_float(r.get("gpu_rows")),
                "util_gpu_pct_max": _to_float(r.get("util_gpu_pct_max")),
                "power_w_sum": _to_float(r.get("power_w_sum")),
                "temp_c_max": _to_float(r.get("temp_c_max")),
                "containers": _to_float(r.get("containers")),
                "load1": _to_float(r.get("load1")),
                "demo_readiness": r.get("demo_readiness", ""),
                "machine_drill_key": r.get("machine_drill_key", ""),
            }
        )

    diversity_rows_out = []
    for r in sorted(compute_div_rows, key=lambda x: (x.get("vendor", ""), x.get("gpu_model", ""))):
        diversity_rows_out.append(
            {
                "as_of_date": r.get("as_of_date", ""),
                "vendor": r.get("vendor", ""),
                "gpu_model": r.get("gpu_model", ""),
                "registered_hosts": _to_float(r.get("registered_hosts")),
                "observed_hosts": _to_float(r.get("observed_hosts")),
                "expected_gpu_count": _to_float(r.get("expected_gpu_count")),
                "reporting_gpu_count": _to_float(r.get("reporting_gpu_count")),
                "telemetry_coverage_pct": _to_float(r.get("telemetry_coverage_pct")),
                "compatibility_status": r.get("compatibility_status", ""),
                "compatibility_note": r.get("compatibility_note", ""),
                "gpu_model_raw_examples": r.get("gpu_model_raw_examples", ""),
            }
        )

    # Provider coverage edge/prod split
    provider_cov_rows = []
    for r in fleet_summary_rows:
        plane = r.get("plane", "")
        provider_cov_rows.append(
            {
                "plane": plane,
                "registered_machines": _to_float(r.get("registered_machines")),
                "observed_machines": _to_float(r.get("observed_machines")),
                "reporting_machines": _to_float(r.get("reporting_machines")),
                "telemetry_coverage_pct": _to_float(r.get("telemetry_coverage_pct")),
                "expected_gpu_count": _to_float(r.get("expected_gpu_count")),
                "reporting_gpu_count": _to_float(r.get("reporting_gpu_count")),
                "gpu_telemetry_coverage_pct": _to_float(r.get("gpu_telemetry_coverage_pct")),
                "healthy_available_machines": _to_float(r.get("healthy_available_machines")),
                "availability_pct": _to_float(r.get("availability_pct")),
                "unmonitored_machines": _to_float(r.get("unmonitored_machines")),
                "confirmed_offline_machines": _to_float(r.get("confirmed_offline_machines")),
                "degraded_machines": _to_float(r.get("degraded_machines")),
                "latest_telemetry_ts": r.get("latest_telemetry_ts", ""),
                "coverage_status": "MEASURED" if plane == "edge" else "UNAVAILABLE",
                "coverage_note": (
                    "Edge telemetry measured in snapshot." if plane == "edge" else "No governed production telemetry row in snapshot."
                ),
            }
        )

    # Machine drill records from overview + detail rollups
    detail_by_host: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in fleet_detail_rows:
        detail_by_host[r.get("host", "")].append(r)

    machine_drill_rows = []
    for ov in sorted(fleet_overview_rows, key=lambda x: x.get("host", "")):
        host = ov.get("host", "")
        drows = detail_by_host.get(host, [])
        util_vals = [_to_float(r.get("util_gpu_pct")) for r in drows if _to_float(r.get("util_gpu_pct")) is not None]
        vram_vals = [_to_float(r.get("vram_pct")) for r in drows if _to_float(r.get("vram_pct")) is not None]
        power_vals = [_to_float(r.get("power_w")) for r in drows if _to_float(r.get("power_w")) is not None]
        temp_vals = [_to_float(r.get("temp_c")) for r in drows if _to_float(r.get("temp_c")) is not None]
        cont_vals = [_to_float(r.get("containers")) for r in drows if _to_float(r.get("containers")) is not None]
        load_vals = [_to_float(r.get("load1")) for r in drows if _to_float(r.get("load1")) is not None]
        gpu_fault_rows = sum(
            1
            for r in drows
            if (_to_bool(r.get("gpu_fault_flag")) is True) or (str(r.get("gpu_status", "")).strip().lower() == "fault")
        )
        machine_drill_rows.append(
            {
                "host": host,
                "display_name": ov.get("display_name", ""),
                "vendor": ov.get("vendor", ""),
                "state": ov.get("state", ""),
                "machine_health_state": ov.get("machine_health_state", ""),
                "telemetry_status": ov.get("telemetry_status", ""),
                "last_sample_ts": ov.get("last_sample_ts", ""),
                "age_s": _to_float(ov.get("age_s")),
                "expected_gpus": _to_float(ov.get("expected_gpus")),
                "reporting_gpu_rows": _to_float(ov.get("gpu_rows")),
                "sample_rows": len(drows),
                "util_samples": len(util_vals),
                "util_avg_pct": mean(util_vals) if util_vals else None,
                "util_p95_pct": _p95(util_vals),
                "vram_samples": len(vram_vals),
                "vram_avg_pct": mean(vram_vals) if vram_vals else None,
                "power_avg_w": mean(power_vals) if power_vals else None,
                "temp_max_c": max(temp_vals) if temp_vals else None,
                "containers_max": max(cont_vals) if cont_vals else None,
                "load1_max": max(load_vals) if load_vals else None,
                "gpu_fault_rows": gpu_fault_rows,
                "demo_readiness": ov.get("demo_readiness", ""),
                "machine_drill_key": ov.get("machine_drill_key", ""),
            }
        )

    machine_gpu_rows = []
    for r in sorted(fleet_detail_rows, key=lambda x: (x.get("host", ""), x.get("sample_ts", ""), x.get("gpu_index", ""))):
        machine_gpu_rows.append(
            {
                "host": r.get("host", ""),
                "sample_ts": r.get("sample_ts", ""),
                "gpu_index": r.get("gpu_index", ""),
                "vendor": r.get("vendor", ""),
                "gpu_name": r.get("gpu_name", ""),
                "driver_version": r.get("driver_version", ""),
                "gpu_status": r.get("gpu_status", ""),
                "util_gpu_pct": _to_float(r.get("util_gpu_pct")),
                "mem_used_mib": _to_float(r.get("mem_used_mib")),
                "mem_total_mib": _to_float(r.get("mem_total_mib")),
                "vram_pct": _to_float(r.get("vram_pct")),
                "power_w": _to_float(r.get("power_w")),
                "temp_c": _to_float(r.get("temp_c")),
                "containers": _to_float(r.get("containers")),
                "load1": _to_float(r.get("load1")),
                "gpu_fault_flag": r.get("gpu_fault_flag", ""),
                "workload_id": r.get("workload_id", ""),
                "workload_join_note": r.get("workload_join_note", ""),
            }
        )

    # Job drill records: enrich job table with runtime/cost prediction diagnostics
    runtime_by_workload: Dict[str, Dict[str, object]] = {}
    for wid in sorted({r.get("workload_id", "") for r in runtime_matched if r.get("workload_id", "")}):
        rows = [r for r in runtime_matched if r.get("workload_id", "") == wid]
        pred = [_to_float(r.get("predicted_runtime_hours")) for r in rows if _to_float(r.get("predicted_runtime_hours")) is not None]
        act = [_to_float(r.get("actual_runtime_hours")) for r in rows if _to_float(r.get("actual_runtime_hours")) is not None]
        ape = [_to_float(r.get("runtime_abs_pct_error")) for r in rows if _to_float(r.get("runtime_abs_pct_error")) is not None]
        under = [_to_bool(r.get("runtime_underestimate_flag")) for r in rows if _to_bool(r.get("runtime_underestimate_flag")) is not None]
        runtime_by_workload[wid] = {
            "runtime_prediction_rows": len(rows),
            "predicted_runtime_hours_avg": mean(pred) if pred else None,
            "actual_runtime_hours_avg": mean(act) if act else None,
            "runtime_abs_pct_error_avg": (mean(ape) * 100) if ape else None,
            "runtime_underestimation_rate_pct": _safe_pct(sum(1 for u in under if u), len(under)) if under else None,
            "runtime_latest_prediction_ts": _max_ts(rows, "prediction_ts"),
            "runtime_status_mode": Counter([r.get("job_status") or "unknown" for r in rows]).most_common(1)[0][0],
        }

    cost_by_workload: Dict[str, Dict[str, object]] = {}
    for wid in sorted({r.get("workload_id", "") for r in pricing_matched if r.get("workload_id", "")}):
        rows = [r for r in pricing_matched if r.get("workload_id", "") == wid]
        est = [_to_float(r.get("estimated_total_cost_usd")) for r in rows if _to_float(r.get("estimated_total_cost_usd")) is not None]
        act = [_to_float(r.get("actual_operational_cost_usd")) for r in rows if _to_float(r.get("actual_operational_cost_usd")) is not None]
        ape = [_to_float(r.get("cost_abs_pct_error")) for r in rows if _to_float(r.get("cost_abs_pct_error")) is not None]
        under = [_to_bool(r.get("cost_underestimate_flag")) for r in rows if _to_bool(r.get("cost_underestimate_flag")) is not None]
        cost_by_workload[wid] = {
            "cost_prediction_rows": len(rows),
            "estimated_total_cost_usd_avg": mean(est) if est else None,
            "actual_operational_cost_usd_avg": mean(act) if act else None,
            "cost_abs_pct_error_avg": (mean(ape) * 100) if ape else None,
            "cost_underestimation_rate_pct": _safe_pct(sum(1 for u in under if u), len(under)) if under else None,
            "cost_latest_prediction_ts": _max_ts(rows, "prediction_ts"),
        }

    job_drill_rows = []
    for j in sorted(job_rows, key=lambda x: x.get("workload_id", "")):
        wid = j.get("workload_id", "")
        rt = runtime_by_workload.get(wid, {})
        ct = cost_by_workload.get(wid, {})
        job_drill_rows.append(
            {
                "workload_id": wid,
                "provider": j.get("provider", ""),
                "workload_type": j.get("workload_type", ""),
                "model_id": j.get("model_id", ""),
                "submitted_at": j.get("submitted_at", ""),
                "trainer_started_at": j.get("trainer_started_at", ""),
                "training_ended_at": j.get("training_ended_at", ""),
                "model_available_at": j.get("model_available_at", ""),
                "payload_status": j.get("payload_status", ""),
                "outcome_status": j.get("outcome_status", ""),
                "failure_class": j.get("failure_class", ""),
                "failure_message_redacted": j.get("failure_message_redacted", ""),
                "wall_time_min": _to_float(j.get("wall_time_min")),
                "training_time_min": _to_float(j.get("training_time_min")),
                "assigned_nodes": j.get("assigned_nodes", ""),
                "assigned_gpus": j.get("assigned_gpus", ""),
                "runtime_prediction_rows": rt.get("runtime_prediction_rows", 0),
                "predicted_runtime_hours_avg": rt.get("predicted_runtime_hours_avg", None),
                "actual_runtime_hours_avg": rt.get("actual_runtime_hours_avg", None),
                "runtime_abs_pct_error_avg": rt.get("runtime_abs_pct_error_avg", None),
                "runtime_underestimation_rate_pct": rt.get("runtime_underestimation_rate_pct", None),
                "runtime_status_mode": rt.get("runtime_status_mode", ""),
                "cost_prediction_rows": ct.get("cost_prediction_rows", 0),
                "estimated_total_cost_usd_avg": ct.get("estimated_total_cost_usd_avg", None),
                "actual_operational_cost_usd_avg": ct.get("actual_operational_cost_usd_avg", None),
                "cost_abs_pct_error_avg": ct.get("cost_abs_pct_error_avg", None),
                "cost_underestimation_rate_pct": ct.get("cost_underestimation_rate_pct", None),
                "as_of_ts": j.get("as_of_ts", ""),
            }
        )

    # Unmatched predictions: keep as separate investigation table
    unmatched_prediction_rows = []
    for r in sorted([x for x in runtime_rows if x.get("match_status") == "unmatched_prediction"], key=lambda x: x.get("prediction_ts", "")):
        unmatched_prediction_rows.append(
            {
                "prediction_ts": r.get("prediction_ts", ""),
                "prediction_date": r.get("prediction_date", ""),
                "prediction_year_week": r.get("prediction_year_week", ""),
                "session_id": r.get("session_id", ""),
                "message_id": r.get("message_id", ""),
                "predicted_model_id": r.get("predicted_model_id", ""),
                "predicted_dataset_ref": r.get("predicted_dataset_ref", ""),
                "predicted_sample_count": _to_float(r.get("predicted_sample_count")),
                "predicted_runtime_hours": _to_float(r.get("predicted_runtime_hours")),
                "predicted_operational_cost_usd": _to_float(r.get("predicted_operational_cost_usd")),
                "scheduler_status": r.get("scheduler_status", ""),
                "job_status": r.get("job_status", ""),
                "missing_actual_runtime": r.get("missing_actual_runtime", ""),
                "match_status": r.get("match_status", ""),
            }
        )

    # Scheduler economics status
    throughput_n = sum(1 for r in scheduler_rows if _to_float(r.get("throughput_tokens_per_s")) is not None)
    supplier_n = sum(1 for r in scheduler_rows if _to_float(r.get("supplier_cost_per_million_usd")) is not None)
    buyer_n = sum(1 for r in scheduler_rows if _to_float(r.get("buyer_price_per_million_usd")) is not None)
    margin_n = sum(1 for r in scheduler_rows if _to_float(r.get("contribution_margin_pct")) is not None)
    scheduler_status_rows = [
        {
            "metric": "Throughput tokens per second",
            "status": "UNAVAILABLE" if throughput_n == 0 else "MEASURED",
            "measured_rows": throughput_n,
            "total_rows": len(scheduler_rows),
            "note": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
        },
        {
            "metric": "Supplier cost per million tokens",
            "status": "UNAVAILABLE" if supplier_n == 0 else "MEASURED",
            "measured_rows": supplier_n,
            "total_rows": len(scheduler_rows),
            "note": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
        },
        {
            "metric": "Buyer price per million tokens",
            "status": "UNAVAILABLE" if buyer_n == 0 else "MEASURED",
            "measured_rows": buyer_n,
            "total_rows": len(scheduler_rows),
            "note": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
        },
        {
            "metric": "Contribution margin pct",
            "status": "UNAVAILABLE" if margin_n == 0 else "MEASURED",
            "measured_rows": margin_n,
            "total_rows": len(scheduler_rows),
            "note": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
        },
    ]

    # Executive cards (6 headline KPI cards)
    edge_row = next((r for r in fleet_summary_rows if (r.get("plane") or "") == "edge"), None)
    edge_cov = _to_float(edge_row.get("telemetry_coverage_pct")) if edge_row else None
    edge_report = _to_float(edge_row.get("reporting_machines")) if edge_row else None
    edge_reg = _to_float(edge_row.get("registered_machines")) if edge_row else None

    commercial_supported_count = sum(1 for r in commercial_comp_rows if r.get("comparison_supported") == "true")
    commercial_total_pairs = len(commercial_comp_rows)

    executive_cards = [
        {
            "card_order": 1,
            "card_key": "workload_success_rate",
            "card_title": "Workload success rate (matched jobs)",
            "value_display": _fmt_pct(workload_success_pct),
            "value_numeric": workload_success_pct,
            "unit": "%",
            "status": "MEASURED",
            "coverage_display": f"{len(runtime_completed)} / {len(runtime_matched)} matched jobs",
            "freshness_ts": _max_ts(runtime_rows, "prediction_ts") or "",
            "detail_note": "Completed / matched jobs from digester runtime cohort.",
        },
        {
            "card_order": 2,
            "card_key": "avg_gpu_utilization",
            "card_title": "Average GPU utilization (edge telemetry)",
            "value_display": _fmt_pct(avg_gpu_util),
            "value_numeric": avg_gpu_util,
            "unit": "%",
            "status": "MEASURED",
            "coverage_display": f"{sum(int(r['util_rows']) for r in util_ts_rows)} util samples / {sum(int(r['sample_rows']) for r in util_ts_rows)} rows",
            "freshness_ts": _max_ts(fleet_detail_rows, "sample_ts") or "",
            "detail_note": "Average of util_gpu_pct where telemetry field is present.",
        },
        {
            "card_order": 3,
            "card_key": "peak_concurrency",
            "card_title": "Peak concurrent GPU jobs",
            "value_display": _fmt_num(peak_gpu_jobs),
            "value_numeric": peak_gpu_jobs,
            "unit": "jobs",
            "status": "MEASURED",
            "coverage_display": f"{len(concurrency_rows)} event timestamps",
            "freshness_ts": _max_ts(concurrency_rows, "ts") or "",
            "detail_note": f"Peak concurrent users observed: {_fmt_num(peak_users)}.",
        },
        {
            "card_order": 4,
            "card_key": "completed_jobs",
            "card_title": "Completed jobs in estimation cohort",
            "value_display": _fmt_num(float(len(runtime_completed_with_actual))),
            "value_numeric": float(len(runtime_completed_with_actual)),
            "unit": "jobs",
            "status": "MEASURED",
            "coverage_display": "Completed matched jobs with actual runtime+cost",
            "freshness_ts": _max_ts(runtime_rows, "prediction_ts") or "",
            "detail_note": "Cohort used for runtime/cost MAPE and underestimation rates.",
        },
        {
            "card_order": 5,
            "card_key": "edge_telemetry_coverage",
            "card_title": "Edge fleet telemetry coverage",
            "value_display": _fmt_pct(edge_cov),
            "value_numeric": edge_cov,
            "unit": "%",
            "status": "MEASURED" if edge_cov is not None else "UNAVAILABLE",
            "coverage_display": f"{_fmt_num(edge_report)} / {_fmt_num(edge_reg)} machines reporting" if edge_row else "N/A",
            "freshness_ts": (edge_row or {}).get("latest_telemetry_ts", "") if edge_row else "",
            "detail_note": "Production plane coverage unavailable in current governed snapshot.",
        },
        {
            "card_order": 6,
            "card_key": "commercial_comparison",
            "card_title": "Commercial comparability (Odyn vs Together)",
            "value_display": "N/A",
            "value_numeric": "",
            "unit": "USD / 1M tokens",
            "status": "UNAVAILABLE",
            "coverage_display": f"{commercial_supported_count} / {commercial_total_pairs} comparable model/workload pairs",
            "freshness_ts": _max_ts(commercial_rows, "as_of_ts") or "",
            "detail_note": "Cost-per-million fields are missing in governed BigQuery extract.",
        },
    ]

    # KPI semantic model dictionary
    freshness_ts = freshness_rows[0].get("inspected_at", "") if freshness_rows else ""
    semantic_rows = [
        {
            "kpi_id": "kpi_workload_success_rate",
            "section": "Executive / Utilisation-Reliability",
            "business_meaning": "Share of matched digester jobs that completed successfully.",
            "unit": "%",
            "aggregation_rule": "Completed matched jobs / Total matched jobs",
            "sample_size": len(runtime_matched),
            "coverage_note": "Matched digester runtime cohort only (not full platform universe).",
            "measurement_status": "MEASURED",
            "current_value": workload_success_pct,
            "visual_recommendation": "KPI card + stacked weekly outcome bar chart",
            "source_table": "tableau_ceo_digester_runtime_accuracy_v1",
            "freshness_ts": freshness_ts,
            "missing_data_policy": "Do not impute unknown statuses as failures or successes.",
        },
        {
            "kpi_id": "kpi_gpu_utilization_avg",
            "section": "Executive / Utilisation-Reliability",
            "business_meaning": "Average observed GPU utilization percentage across telemetry rows with util field present.",
            "unit": "%",
            "aggregation_rule": "Mean(util_gpu_pct) across non-null util rows; never over all rows.",
            "sample_size": sum(int(r["util_rows"]) for r in util_ts_rows),
            "coverage_note": "Edge telemetry only in this snapshot.",
            "measurement_status": "MEASURED",
            "current_value": avg_gpu_util,
            "visual_recommendation": "Time-series line with 50% reference line",
            "source_table": "tableau_ceo_fleet_machine_detail_v1",
            "freshness_ts": _max_ts(fleet_detail_rows, "sample_ts") or freshness_ts,
            "missing_data_policy": "Keep rows without util as missing; show coverage separately.",
        },
        {
            "kpi_id": "kpi_peak_concurrent_gpu_jobs",
            "section": "Executive / Utilisation-Reliability",
            "business_meaning": "Maximum observed simultaneous GPU jobs.",
            "unit": "jobs",
            "aggregation_rule": "Max(concurrent_gpu_jobs)",
            "sample_size": len(concurrency_rows),
            "coverage_note": "Event-level concurrency extract.",
            "measurement_status": "MEASURED",
            "current_value": peak_gpu_jobs,
            "visual_recommendation": "KPI card + event timeline line",
            "source_table": "tableau_ceo_concurrency_v1",
            "freshness_ts": _max_ts(concurrency_rows, "ts") or freshness_ts,
            "missing_data_policy": "No interpolation required for sparse events.",
        },
        {
            "kpi_id": "kpi_runtime_mape",
            "section": "Estimation/Pricing",
            "business_meaning": "Average absolute percentage runtime prediction error.",
            "unit": "%",
            "aggregation_rule": "Mean(runtime_abs_pct_error) * 100 on completed matched jobs with actual runtime",
            "sample_size": len(runtime_completed_with_actual),
            "coverage_note": "Completed matched cohort only.",
            "measurement_status": "MEASURED",
            "current_value": runtime_mape_pct,
            "visual_recommendation": "KPI card + predicted vs actual runtime scatter",
            "source_table": "tableau_ceo_digester_runtime_accuracy_v1",
            "freshness_ts": _max_ts(runtime_rows, "prediction_ts") or freshness_ts,
            "missing_data_policy": "Exclude rows where actual runtime is missing; do not set to zero.",
        },
        {
            "kpi_id": "kpi_cost_mape",
            "section": "Estimation/Pricing",
            "business_meaning": "Average absolute percentage operational cost prediction error.",
            "unit": "%",
            "aggregation_rule": "Mean(cost_abs_pct_error) * 100 on completed matched jobs with actual cost",
            "sample_size": len(pricing_completed_with_actual),
            "coverage_note": "Completed matched cohort only.",
            "measurement_status": "MEASURED",
            "current_value": cost_mape_pct,
            "visual_recommendation": "KPI card + predicted vs actual cost scatter",
            "source_table": "tableau_ceo_digester_pricing_accuracy_v1",
            "freshness_ts": _max_ts(pricing_rows, "prediction_ts") or freshness_ts,
            "missing_data_policy": "Exclude rows where actual cost is missing; do not set to zero.",
        },
        {
            "kpi_id": "kpi_runtime_underestimation_rate",
            "section": "Estimation/Pricing",
            "business_meaning": "Rate where predicted runtime is below actual runtime.",
            "unit": "%",
            "aggregation_rule": "Count(runtime_underestimate_flag=true) / N",
            "sample_size": len(runtime_completed_with_actual),
            "coverage_note": "Wilson 95% interval provided for transparency.",
            "measurement_status": "MEASURED",
            "current_value": runtime_under_pct,
            "visual_recommendation": "KPI card with CI annotation",
            "source_table": "tableau_ceo_digester_runtime_accuracy_v1",
            "freshness_ts": _max_ts(runtime_rows, "prediction_ts") or freshness_ts,
            "missing_data_policy": "Exclude rows without valid under/over flag.",
        },
        {
            "kpi_id": "kpi_cost_underestimation_rate",
            "section": "Estimation/Pricing",
            "business_meaning": "Rate where estimated cost is below actual operational cost.",
            "unit": "%",
            "aggregation_rule": "Count(cost_underestimate_flag=true) / N",
            "sample_size": len(pricing_completed_with_actual),
            "coverage_note": "Wilson 95% interval provided for transparency.",
            "measurement_status": "MEASURED",
            "current_value": cost_under_pct,
            "visual_recommendation": "KPI card with CI annotation",
            "source_table": "tableau_ceo_digester_pricing_accuracy_v1",
            "freshness_ts": _max_ts(pricing_rows, "prediction_ts") or freshness_ts,
            "missing_data_policy": "Exclude rows without valid under/over flag.",
        },
        {
            "kpi_id": "kpi_commercial_cost_per_million",
            "section": "Commercial",
            "business_meaning": "Supplier/buyer economics in USD per million tokens for provider comparison.",
            "unit": "USD / 1M tokens",
            "aggregation_rule": "Provider/model/workload matched comparison only",
            "sample_size": len(commercial_rows),
            "coverage_note": "Token and governed pricing joins missing.",
            "measurement_status": "UNAVAILABLE",
            "current_value": "",
            "visual_recommendation": "N/A status card + comparability coverage table",
            "source_table": "tableau_ceo_commercial_benchmark_v1",
            "freshness_ts": _max_ts(commercial_rows, "as_of_ts") or freshness_ts,
            "missing_data_policy": "Display N/A; never display zero cost for unavailable values.",
        },
        {
            "kpi_id": "kpi_vram_accuracy",
            "section": "Digester Quality",
            "business_meaning": "VRAM prediction error accuracy from observed peak VRAM matches.",
            "unit": "%",
            "aggregation_rule": "Would be MAPE on rows with observed VRAM",
            "sample_size": len(vram_rows),
            "coverage_note": f"Observed VRAM present on {len(observed_vram)}/{len(vram_rows)} rows.",
            "measurement_status": "UNAVAILABLE",
            "current_value": "",
            "visual_recommendation": "N/A status card with coverage explanation",
            "source_table": "tableau_ceo_digester_vram_accuracy_v1",
            "freshness_ts": _max_ts(vram_rows, "prediction_ts") or freshness_ts,
            "missing_data_policy": "Insufficient observed coverage; do not synthesize metric.",
        },
        {
            "kpi_id": "kpi_langsmith_eval",
            "section": "Digester Quality",
            "business_meaning": "Hallucination/quality score from governed LangSmith evaluations.",
            "unit": "score",
            "aggregation_rule": "Model/workload evaluation average (if data exists)",
            "sample_size": len(eval_rows),
            "coverage_note": "No governed evaluation rows in snapshot.",
            "measurement_status": "UNAVAILABLE",
            "current_value": "",
            "visual_recommendation": "N/A status card",
            "source_table": "tableau_ceo_digester_evaluations_v1",
            "freshness_ts": freshness_ts,
            "missing_data_policy": "Display N/A only.",
        },
        {
            "kpi_id": "kpi_scheduler_economics",
            "section": "Scheduler Economics",
            "business_meaning": "Measured throughput and cost/margin economics of scheduler decisions.",
            "unit": "USD / 1M tokens and tokens/s",
            "aggregation_rule": "Summaries on rows with governed throughput + price + supplier cost",
            "sample_size": len(scheduler_rows),
            "coverage_note": "All economics measure columns missing in current governed snapshot.",
            "measurement_status": "UNAVAILABLE",
            "current_value": "",
            "visual_recommendation": "N/A status card + evidence table",
            "source_table": "tableau_ceo_scheduler_economics_v1",
            "freshness_ts": _max_ts(scheduler_rows, "as_of_ts") or freshness_ts,
            "missing_data_policy": "Display N/A; do not use placeholder zeros.",
        },
    ]

    # Render QA template (to be completed in Tableau native UI)
    qa_rows = []
    worksheet_specs = [
        "Executive KPI Cards",
        "GPU Utilization Trend",
        "Workload Outcome Breakdown",
        "Commercial Comparability",
        "Estimation Accuracy KPI Cards",
        "Runtime Predicted vs Actual Scatter",
        "Cost Predicted vs Actual Scatter",
        "Digester Availability Cards",
        "Fleet Health Summary",
        "GPU Model Distribution",
        "Machine Drill Summary",
        "Machine Drill Telemetry Detail",
        "Job Drill Summary",
        "Job Drill Detail",
        "Scheduler Economics Status",
    ]
    for ws in worksheet_specs:
        qa_rows.append(
            {
                "worksheet": ws,
                "business_question_answered": "PENDING_NATIVE_RENDER_QA",
                "correct_unit_axis": "PENDING_NATIVE_RENDER_QA",
                "valid_aggregation": "PENDING_NATIVE_RENDER_QA",
                "records_support_result": "PENDING_NATIVE_RENDER_QA",
                "missing_data_truthful": "PENDING_NATIVE_RENDER_QA",
                "legible_and_useful": "PENDING_NATIVE_RENDER_QA",
                "notes": "Complete in Tableau Cloud/Desktop after visual render inspection.",
            }
        )

    # Write all assets
    _write_csv(
        OUT / "semantic_kpi_model.csv",
        semantic_rows,
        [
            "kpi_id",
            "section",
            "business_meaning",
            "unit",
            "aggregation_rule",
            "sample_size",
            "coverage_note",
            "measurement_status",
            "current_value",
            "visual_recommendation",
            "source_table",
            "freshness_ts",
            "missing_data_policy",
        ],
    )

    _write_csv(
        OUT / "executive_kpi_cards.csv",
        executive_cards,
        [
            "card_order",
            "card_key",
            "card_title",
            "value_display",
            "value_numeric",
            "unit",
            "status",
            "coverage_display",
            "freshness_ts",
            "detail_note",
        ],
    )

    _write_csv(
        OUT / "gpu_utilization_timeseries.csv",
        util_ts_rows,
        [
            "sample_ts",
            "sample_date",
            "sample_rows",
            "util_rows",
            "util_coverage_pct",
            "avg_gpu_utilization_pct",
            "reference_line_pct",
            "plane",
            "note",
        ],
    )

    _write_csv(
        OUT / "concurrency_timeline.csv",
        conc_rows,
        ["ts", "metric_date", "concurrent_gpu_jobs", "concurrent_users"],
    )

    _write_csv(
        OUT / "workload_outcomes_by_week.csv",
        outcome_rows,
        [
            "year_week",
            "completed_jobs",
            "failed_jobs",
            "stopped_jobs",
            "unknown_jobs",
            "total_jobs",
            "success_rate_pct",
            "failure_or_stop_rate_pct",
        ],
    )

    _write_csv(
        OUT / "oom_failure_breakdown.csv",
        oom_rows,
        ["year_week", "failure_bucket", "jobs", "share_of_failures_pct", "total_failed_or_stopped_jobs"],
    )

    _write_csv(
        OUT / "commercial_comparability.csv",
        commercial_comp_rows,
        [
            "workload_type",
            "model_id",
            "odyn_rows",
            "together_rows",
            "odyn_cost_rows",
            "together_cost_rows",
            "comparison_supported",
            "status",
            "na_reason",
        ],
    )

    _write_csv(
        OUT / "digester_availability_cards.csv",
        digester_availability_rows,
        [
            "metric",
            "status",
            "coverage_n",
            "coverage_denominator",
            "coverage_pct",
            "value",
            "unit",
            "explanation",
        ],
    )

    _write_csv(
        OUT / "estimation_accuracy_summary.csv",
        estimation_summary_rows,
        [
            "metric",
            "value_pct",
            "sample_size_n",
            "denominator_note",
            "status",
            "ci_low_pct",
            "ci_high_pct",
            "value_display",
        ],
    )

    _write_csv(
        OUT / "runtime_scatter_points.csv",
        runtime_scatter_rows,
        [
            "workload_id",
            "job_id",
            "prediction_date",
            "prediction_year_week",
            "model_id",
            "predicted_runtime_hours",
            "actual_runtime_hours",
            "runtime_abs_pct_error",
            "runtime_underestimate_flag",
            "selected_gpu_tier",
            "selected_gpu_count",
        ],
    )

    _write_csv(
        OUT / "cost_scatter_points.csv",
        cost_scatter_rows,
        [
            "workload_id",
            "job_id",
            "prediction_date",
            "prediction_year_week",
            "model_id",
            "estimated_total_cost_usd",
            "actual_operational_cost_usd",
            "cost_abs_pct_error",
            "cost_underestimate_flag",
            "selected_gpu_tier",
            "selected_gpu_count",
        ],
    )

    _write_csv(
        OUT / "fleet_health_overview.csv",
        fleet_overview_rows_out,
        [
            "host",
            "display_name",
            "vendor",
            "state",
            "machine_health_state",
            "telemetry_status",
            "telemetry_fresh",
            "last_sample_ts",
            "age_s",
            "expected_gpus",
            "gpu_rows",
            "util_gpu_pct_max",
            "power_w_sum",
            "temp_c_max",
            "containers",
            "load1",
            "demo_readiness",
            "machine_drill_key",
        ],
    )

    _write_csv(
        OUT / "fleet_gpu_model_distribution.csv",
        diversity_rows_out,
        [
            "as_of_date",
            "vendor",
            "gpu_model",
            "registered_hosts",
            "observed_hosts",
            "expected_gpu_count",
            "reporting_gpu_count",
            "telemetry_coverage_pct",
            "compatibility_status",
            "compatibility_note",
            "gpu_model_raw_examples",
        ],
    )

    _write_csv(
        OUT / "provider_coverage.csv",
        provider_cov_rows,
        [
            "plane",
            "registered_machines",
            "observed_machines",
            "reporting_machines",
            "telemetry_coverage_pct",
            "expected_gpu_count",
            "reporting_gpu_count",
            "gpu_telemetry_coverage_pct",
            "healthy_available_machines",
            "availability_pct",
            "unmonitored_machines",
            "confirmed_offline_machines",
            "degraded_machines",
            "latest_telemetry_ts",
            "coverage_status",
            "coverage_note",
        ],
    )

    _write_csv(
        OUT / "machine_drill_records.csv",
        machine_drill_rows,
        [
            "host",
            "display_name",
            "vendor",
            "state",
            "machine_health_state",
            "telemetry_status",
            "last_sample_ts",
            "age_s",
            "expected_gpus",
            "reporting_gpu_rows",
            "sample_rows",
            "util_samples",
            "util_avg_pct",
            "util_p95_pct",
            "vram_samples",
            "vram_avg_pct",
            "power_avg_w",
            "temp_max_c",
            "containers_max",
            "load1_max",
            "gpu_fault_rows",
            "demo_readiness",
            "machine_drill_key",
        ],
    )

    _write_csv(
        OUT / "machine_gpu_telemetry_records.csv",
        machine_gpu_rows,
        [
            "host",
            "sample_ts",
            "gpu_index",
            "vendor",
            "gpu_name",
            "driver_version",
            "gpu_status",
            "util_gpu_pct",
            "mem_used_mib",
            "mem_total_mib",
            "vram_pct",
            "power_w",
            "temp_c",
            "containers",
            "load1",
            "gpu_fault_flag",
            "workload_id",
            "workload_join_note",
        ],
    )

    _write_csv(
        OUT / "job_drill_records.csv",
        job_drill_rows,
        [
            "workload_id",
            "provider",
            "workload_type",
            "model_id",
            "submitted_at",
            "trainer_started_at",
            "training_ended_at",
            "model_available_at",
            "payload_status",
            "outcome_status",
            "failure_class",
            "failure_message_redacted",
            "wall_time_min",
            "training_time_min",
            "assigned_nodes",
            "assigned_gpus",
            "runtime_prediction_rows",
            "predicted_runtime_hours_avg",
            "actual_runtime_hours_avg",
            "runtime_abs_pct_error_avg",
            "runtime_underestimation_rate_pct",
            "runtime_status_mode",
            "cost_prediction_rows",
            "estimated_total_cost_usd_avg",
            "actual_operational_cost_usd_avg",
            "cost_abs_pct_error_avg",
            "cost_underestimation_rate_pct",
            "as_of_ts",
        ],
    )

    _write_csv(
        OUT / "unmatched_predictions.csv",
        unmatched_prediction_rows,
        [
            "prediction_ts",
            "prediction_date",
            "prediction_year_week",
            "session_id",
            "message_id",
            "predicted_model_id",
            "predicted_dataset_ref",
            "predicted_sample_count",
            "predicted_runtime_hours",
            "predicted_operational_cost_usd",
            "scheduler_status",
            "job_status",
            "missing_actual_runtime",
            "match_status",
        ],
    )

    _write_csv(
        OUT / "scheduler_economics_status.csv",
        scheduler_status_rows,
        ["metric", "status", "measured_rows", "total_rows", "note"],
    )

    _write_csv(
        OUT / "render_validation_checklist_template.csv",
        qa_rows,
        [
            "worksheet",
            "business_question_answered",
            "correct_unit_axis",
            "valid_aggregation",
            "records_support_result",
            "missing_data_truthful",
            "legible_and_useful",
            "notes",
        ],
    )

    summary = {
        "runtime_completed_with_actual_n": len(runtime_completed_with_actual),
        "pricing_completed_with_actual_n": len(pricing_completed_with_actual),
        "runtime_mape_pct": runtime_mape_pct,
        "cost_mape_pct": cost_mape_pct,
        "runtime_underestimation_pct": runtime_under_pct,
        "cost_underestimation_pct": cost_under_pct,
        "workload_success_rate_pct": workload_success_pct,
        "matched_jobs_n": len(runtime_matched),
        "completed_jobs_n": len(runtime_completed),
        "failed_or_stopped_n": len(failed_or_stopped),
        "oom_failures_n": len(oom_failures),
        "commercial_pairs_total": commercial_total_pairs,
        "commercial_pairs_supported": commercial_supported_count,
        "vram_observed_rows": len(observed_vram),
        "vram_total_rows": len(vram_rows),
        "langsmith_rows": len(eval_rows),
        "generated_files": sorted([p.name for p in OUT.glob("*.csv")]),
    }
    (OUT / "asset_build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {len(summary['generated_files'])} CSV assets to {OUT}")


if __name__ == "__main__":
    main()

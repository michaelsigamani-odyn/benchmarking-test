#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import uuid
import glob as pyglob
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from urllib.request import Request, urlopen


RAW_TABLE = "raw_ops.workload_conditions_raw_v1"
COND_TABLE = "clean_ops.workload_conditions_v1"
TIME_TABLE = "clean_ops.workload_timing_v1"


SECRET_PATTERNS = [
    re.compile(r"(?i)bearer\\s+[a-z0-9._-]+"),
    re.compile(r"(?i)\\bhf_[a-z0-9]{20,}\\b"),
    re.compile(r"(?i)x-goog-signature="),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)"),
    re.compile(r"\buser_[A-Za-z0-9]+\b"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
]

SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "token",
    "secret",
    "password",
    "owner_address",
    "user_id",
    "signed_url",
}


@dataclass
class BqConfig:
    project: str
    location: str


def _run(cmd: List[str], input_text: str | None = None) -> str:
    proc = subprocess.run(cmd, input=input_text, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def _bq_query(cfg: BqConfig, sql: str) -> str:
    return _run([
        "bq",
        "--project_id",
        cfg.project,
        "--location",
        cfg.location,
        "query",
        "--nouse_legacy_sql",
        "--quiet",
        sql,
    ])


def _bq_scalar_int(cfg: BqConfig, sql: str) -> int:
    out = _run([
        "bq",
        "--project_id",
        cfg.project,
        "--location",
        cfg.location,
        "query",
        "--nouse_legacy_sql",
        "--quiet",
        "--format=csv",
        sql,
    ])
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return 0
    try:
        return int(float(lines[1].split(",")[0]))
    except Exception:
        return 0


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_dt(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _event_date(event_at: Optional[datetime], fetched_at: datetime) -> str:
    return (event_at or fetched_at).date().isoformat()


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sanitize_uri(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if "://" not in raw:
        return raw
    parts = urlsplit(raw)
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return cleaned


def _hmac_hex(key: str, value: Optional[str]) -> Optional[str]:
    if not key or not value:
        return None
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).strip().lower()
            if lk in SENSITIVE_KEYS or any(t in lk for t in ["token", "secret", "password", "api_key", "authorization", "signature"]):
                out[k] = "<REDACTED>"
            else:
                out[k] = _redact_value(v)
        return out
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, str):
        stripped = _sanitize_uri(value) or ""
        if any(p.search(stripped) for p in SECRET_PATTERNS):
            return "<REDACTED>"
        return stripped
    return value


def _scan_findings(value: Any) -> List[str]:
    findings: List[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, vv in v.items():
                if isinstance(k, str):
                    lk = k.lower().strip()
                    if lk in SENSITIVE_KEYS and vv != "<REDACTED>":
                        findings.append(f"unredacted_sensitive_key:{lk}")
                    if any(t in lk for t in ["api_key", "authorization", "password", "secret", "signature"]) and vv != "<REDACTED>":
                        findings.append(f"unredacted_secretish_key:{lk}")
                walk(vv)
        elif isinstance(v, list):
            for i in v:
                walk(i)
        elif isinstance(v, str):
            for idx, pat in enumerate(SECRET_PATTERNS):
                if pat.search(v):
                    findings.append(f"pattern_{idx}")

    walk(value)
    return sorted(set(findings))


def _load_together_rows_from_local(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    for page in payload:
        if not isinstance(page, dict):
            continue
        if not page.get("ok"):
            continue
        stdout = page.get("stdout")
        if not isinstance(stdout, str):
            continue
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            rows.extend([r for r in parsed if isinstance(r, dict)])
    return rows


def _fetch_together_rows_live(max_pages: int, timeout_seconds: int) -> List[Dict[str, Any]]:
    api_key = (os.getenv("TOGETHER_API_KEY") or os.getenv("TOGETHERAI_API_KEY") or "").strip()
    if not api_key:
        return []
    url = os.getenv("TOGETHER_JOBS_URL", "https://api.together.xyz/v1/fine-tunes").strip()
    rows: List[Dict[str, Any]] = []
    pages = 0
    while url and pages < max_pages:
        req = Request(url=url, headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}, method="GET")
        with urlopen(req, timeout=timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, list):
            rows.extend([x for x in payload if isinstance(x, dict)])
            break
        if isinstance(payload, dict):
            data = payload.get("data") if isinstance(payload.get("data"), list) else payload.get("runs")
            if isinstance(data, list):
                rows.extend([x for x in data if isinstance(x, dict)])
            nxt = payload.get("next") or payload.get("next_url")
            url = nxt if isinstance(nxt, str) and nxt.strip() else ""
        else:
            break
        pages += 1
    return rows


def _load_eks_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append(dict(row))
    return out


def _load_together_events_map(events_glob: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for p in pyglob.glob(events_glob):
        path = Path(p)
        m = re.search(r"fine_tuning_job_(ft-[^.]+)\.events\.raw\.json$", path.name)
        if not m:
            continue
        job_id = m.group(1)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, list):
            out[job_id] = [x for x in payload if isinstance(x, dict)]
    return out


def _event_type_ts(events: List[Dict[str, Any]], event_type: str) -> Optional[datetime]:
    for e in events:
        if str(e.get("type") or "").strip().upper() == event_type.upper():
            t = _to_dt(e.get("created_at"))
            if t:
                return t
    return None


def _is_benchmark_together(row: Dict[str, Any]) -> bool:
    suffix = str(row.get("suffix") or "").lower()
    out_name = str(row.get("model_output_name") or row.get("output_name") or "").lower()
    return "bench" in suffix or "bench" in out_name


def _raw_row_from_together(
    row: Dict[str, Any],
    ingest_run_id: str,
    fetched_at: datetime,
    hmac_key: str,
    events_map: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    provider_run_id = str(row.get("id") or "").strip() or f"anon_{_sha256_text(_canonical_json(row))[:16]}"
    event_at = _to_dt(row.get("created_at") or row.get("started_at") or row.get("updated_at"))
    user_id = row.get("user_id")
    owner_address = row.get("owner_address")
    is_benchmark = _is_benchmark_together(row)
    is_customer = not is_benchmark

    payload = dict(row)
    events = events_map.get(provider_run_id)
    if events:
        payload["events"] = events

    payload_redacted = _redact_value(payload)
    findings = _scan_findings(payload_redacted)
    if findings:
        raise RuntimeError(f"redaction scan failed for together run {provider_run_id}: {','.join(findings)}")

    payload_canon = _canonical_json(payload_redacted)
    payload_sha = _sha256_text(payload_canon)
    raw_record_id = _sha256_text(f"together|{provider_run_id}|{payload_sha}|{ingest_run_id}")

    return {
        "raw_record_id": raw_record_id,
        "ingest_run_id": ingest_run_id,
        "fetched_at": fetched_at.isoformat(),
        "event_at": event_at.isoformat() if event_at else None,
        "event_date": _event_date(event_at, fetched_at),
        "source_system": "together_api",
        "provider": "together",
        "workload_type": "finetune",
        "workload_id": provider_run_id,
        "provider_run_id": provider_run_id,
        "is_benchmark_run": is_benchmark,
        "is_customer_workload": is_customer,
        "user_hmac": _hmac_hex(hmac_key, str(user_id)) if user_id else None,
        "owner_hmac": _hmac_hex(hmac_key, str(owner_address)) if owner_address else None,
        "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
        "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
        "redaction_version": "redact_v1",
        "redaction_applied": True,
        "redaction_scan_passed": True,
        "redaction_scan_findings": [],
        "payload_sha256": payload_sha,
        "payload_redacted": payload_redacted,
    }


def _raw_row_from_eks(row: Dict[str, Any], ingest_run_id: str, fetched_at: datetime, hmac_key: str) -> Dict[str, Any]:
    provider_run_id = (row.get("source_finetune_job_id") or "").strip() or f"eks_{uuid.uuid4().hex[:16]}"
    observed = _to_dt(row.get("observed_at"))
    user_id = (row.get("user_id") or "").strip() or None
    payload_redacted = _redact_value(row)
    findings = _scan_findings(payload_redacted)
    if findings:
        raise RuntimeError(f"redaction scan failed for eks row {provider_run_id}: {','.join(findings)}")
    payload_canon = _canonical_json(payload_redacted)
    payload_sha = _sha256_text(payload_canon)
    raw_record_id = _sha256_text(f"odyn|{provider_run_id}|{payload_sha}|{ingest_run_id}")

    return {
        "raw_record_id": raw_record_id,
        "ingest_run_id": ingest_run_id,
        "fetched_at": fetched_at.isoformat(),
        "event_at": observed.isoformat() if observed else None,
        "event_date": _event_date(observed, fetched_at),
        "source_system": "eks_kuberay",
        "provider": "odyn",
        "workload_type": "serving",
        "workload_id": provider_run_id,
        "provider_run_id": provider_run_id,
        "is_benchmark_run": False,
        "is_customer_workload": True,
        "user_hmac": _hmac_hex(hmac_key, user_id) if user_id else None,
        "owner_hmac": None,
        "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
        "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
        "redaction_version": "redact_v1",
        "redaction_applied": True,
        "redaction_scan_passed": True,
        "redaction_scan_findings": [],
        "payload_sha256": payload_sha,
        "payload_redacted": payload_redacted,
    }


def _conditions_from_together(row: Dict[str, Any], ingest_run_id: str, as_of_ts: datetime) -> Dict[str, Any]:
    provider_run_id = str(row.get("id") or "").strip()
    training_type = row.get("training_type") if isinstance(row.get("training_type"), dict) else {}
    method = row.get("training_method") if isinstance(row.get("training_method"), dict) else {}

    batch_raw = row.get("batch_size")
    batch_value = int(batch_raw) if isinstance(batch_raw, int) else None
    batch_kind = "per_device" if batch_value is not None else "unknown"

    dataset_ref = row.get("training_file") or row.get("training_file_id")

    bench = _is_benchmark_together(row)
    customer = not bench

    return {
        "as_of_ts": as_of_ts.isoformat(),
        "provider": "together",
        "workload_id": provider_run_id,
        "workload_type": "finetune",
        "provider_run_id": provider_run_id,
        "is_benchmark_run": bench,
        "is_customer_workload": customer,
        "model_id": row.get("model"),
        "model_id_f": 1 if row.get("model") else 0,
        "model_id_source": "together_api.model",
        "model_id_reason": None if row.get("model") else "missing",
        "training_objective": str(method.get("method") or "unknown").lower(),
        "training_objective_f": 1 if method.get("method") else 0,
        "training_objective_source": "together_api.training_method.method",
        "training_objective_reason": None if method.get("method") else "missing",
        "training_method": "lora" if str(training_type.get("type") or "").lower() == "lora" else "unknown",
        "training_method_f": 1 if training_type else 0,
        "training_method_source": "together_api.training_type.type",
        "training_method_reason": None if training_type else "missing",
        "lora_rank": training_type.get("lora_r") if isinstance(training_type.get("lora_r"), int) else None,
        "lora_rank_f": 1 if isinstance(training_type.get("lora_r"), int) else 0,
        "lora_rank_source": "together_api.training_type.lora_r",
        "lora_rank_reason": None if isinstance(training_type.get("lora_r"), int) else "missing",
        "lora_alpha": training_type.get("lora_alpha") if isinstance(training_type.get("lora_alpha"), int) else None,
        "lora_alpha_f": 1 if isinstance(training_type.get("lora_alpha"), int) else 0,
        "lora_alpha_source": "together_api.training_type.lora_alpha",
        "lora_alpha_reason": None if isinstance(training_type.get("lora_alpha"), int) else "missing",
        "batch_size_value": batch_value,
        "batch_size_raw": str(batch_raw) if batch_raw is not None else None,
        "batch_size_kind": batch_kind,
        "batch_size_f": 1 if batch_value is not None else 0,
        "batch_size_source": "together_api.batch_size",
        "batch_size_reason": None if batch_value is not None else "non-integer-or-missing",
        "learning_rate": float(row["learning_rate"]) if isinstance(row.get("learning_rate"), (int, float)) else None,
        "learning_rate_f": 1 if isinstance(row.get("learning_rate"), (int, float)) else 0,
        "learning_rate_source": "together_api.learning_rate",
        "learning_rate_reason": None if isinstance(row.get("learning_rate"), (int, float)) else "missing",
        "seq_len": int(row["max_seq_length"]) if isinstance(row.get("max_seq_length"), int) else None,
        "seq_len_f": 1 if isinstance(row.get("max_seq_length"), int) else 0,
        "seq_len_source": "together_api.max_seq_length",
        "seq_len_reason": None if isinstance(row.get("max_seq_length"), int) else "missing",
        "gpu_count": None,
        "gpu_count_f": 0,
        "gpu_count_source": "unknown",
        "gpu_count_reason": "not_returned_by_provider",
        "precision": None,
        "precision_f": 0,
        "precision_source": "unknown",
        "precision_reason": "not_returned_by_provider",
        "dataset_uri_sanitized": _sanitize_uri(dataset_ref),
        "dataset_uri_sanitized_f": 1 if dataset_ref else 0,
        "dataset_uri_sanitized_source": "together_api.training_file",
        "dataset_uri_sanitized_reason": None if dataset_ref else "missing",
        "dataset_content_hash": None,
        "dataset_content_hash_f": 0,
        "dataset_content_hash_source": "unavailable",
        "dataset_content_hash_reason": "not available in v1",
        "dataset_identity_hmac": None,
        "dataset_identity_hmac_f": 0,
        "dataset_identity_hmac_source": "unavailable",
        "dataset_identity_hmac_reason": "requires dedicated key pipeline",
        "dataset_identity_hmac_key_version": None,
        "tokenizer_id": None,
        "tokenizer_id_f": 0,
        "tokenizer_id_source": "unknown",
        "tokenizer_id_reason": "not returned",
        "tokenizer_fallback_used": None,
        "tokenizer_fallback_used_f": 0,
        "tokenizer_fallback_reason": "unknown",
        "source_system": "together_api",
        "source_record_ref": None,
        "ingest_run_id": ingest_run_id,
    }


def _conditions_from_eks(row: Dict[str, Any], ingest_run_id: str, as_of_ts: datetime) -> Dict[str, Any]:
    workload_id = (row.get("source_finetune_job_id") or "").strip() or f"eks_{uuid.uuid4().hex[:16]}"
    model = row.get("model_name")
    return {
        "as_of_ts": as_of_ts.isoformat(),
        "provider": "odyn",
        "workload_id": workload_id,
        "workload_type": "serving",
        "provider_run_id": workload_id,
        "is_benchmark_run": False,
        "is_customer_workload": True,
        "model_id": model,
        "model_id_f": 1 if model else 0,
        "model_id_source": "eks_kuberay.model_name",
        "model_id_reason": None if model else "missing",
        "training_objective": "unknown",
        "training_objective_f": 0,
        "training_objective_source": "unknown",
        "training_objective_reason": "serving row",
        "training_method": "unknown",
        "training_method_f": 0,
        "training_method_source": "unknown",
        "training_method_reason": "serving row",
        "lora_rank": None,
        "lora_rank_f": 0,
        "lora_rank_source": "unknown",
        "lora_rank_reason": "serving row",
        "lora_alpha": None,
        "lora_alpha_f": 0,
        "lora_alpha_source": "unknown",
        "lora_alpha_reason": "serving row",
        "batch_size_value": None,
        "batch_size_raw": None,
        "batch_size_kind": "unknown",
        "batch_size_f": 0,
        "batch_size_source": "unknown",
        "batch_size_reason": "not available",
        "learning_rate": None,
        "learning_rate_f": 0,
        "learning_rate_source": "unknown",
        "learning_rate_reason": "serving row",
        "seq_len": None,
        "seq_len_f": 0,
        "seq_len_source": "unknown",
        "seq_len_reason": "not available",
        "gpu_count": None,
        "gpu_count_f": 0,
        "gpu_count_source": "unknown",
        "gpu_count_reason": "not available",
        "precision": None,
        "precision_f": 0,
        "precision_source": "unknown",
        "precision_reason": "not available",
        "dataset_uri_sanitized": None,
        "dataset_uri_sanitized_f": 0,
        "dataset_uri_sanitized_source": "none",
        "dataset_uri_sanitized_reason": "serving row",
        "dataset_content_hash": None,
        "dataset_content_hash_f": 0,
        "dataset_content_hash_source": "none",
        "dataset_content_hash_reason": "serving row",
        "dataset_identity_hmac": None,
        "dataset_identity_hmac_f": 0,
        "dataset_identity_hmac_source": "none",
        "dataset_identity_hmac_reason": "serving row",
        "dataset_identity_hmac_key_version": None,
        "tokenizer_id": None,
        "tokenizer_id_f": 0,
        "tokenizer_id_source": "none",
        "tokenizer_id_reason": "serving row",
        "tokenizer_fallback_used": None,
        "tokenizer_fallback_used_f": 0,
        "tokenizer_fallback_reason": "serving row",
        "source_system": "eks_kuberay",
        "source_record_ref": None,
        "ingest_run_id": ingest_run_id,
    }


def _timing_from_together(
    row: Dict[str, Any],
    ingest_run_id: str,
    as_of_ts: datetime,
    events_map: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    workload_id = str(row.get("id") or "").strip()
    created = _to_dt(row.get("created_at"))
    started = _to_dt(row.get("started_at"))
    updated = _to_dt(row.get("updated_at"))

    events = events_map.get(workload_id, [])
    ev_training_start = _event_type_ts(events, "TRAINING_START")
    ev_training_complete = _event_type_ts(events, "TRAINING_COMPLETE")
    ev_job_complete = _event_type_ts(events, "JOB_COMPLETE")

    trainer_started = ev_training_start or started
    training_ended = ev_training_complete or updated
    model_available = ev_job_complete or updated

    wall = None
    if created and model_available:
        wall = max(0.0, (model_available - created).total_seconds() / 60.0)
    training = None
    if trainer_started and training_ended:
        training = max(0.0, (training_ended - trainer_started).total_seconds() / 60.0)

    return {
        "as_of_ts": as_of_ts.isoformat(),
        "provider": "together",
        "workload_id": workload_id,
        "workload_type": "finetune",
        "submitted_at": created.isoformat() if created else None,
        "submitted_at_f": 1 if created else 0,
        "submitted_at_source": "provider_server_clock",
        "submitted_at_reason": None if created else "missing",
        "model_available_at": model_available.isoformat() if model_available else None,
        "model_available_at_f": 1 if ev_job_complete else (0 if updated else 0),
        "model_available_at_source": "together.events.JOB_COMPLETE" if ev_job_complete else "together.updated_at_proxy",
        "model_available_at_reason": None if ev_job_complete else "updated_at is generic update timestamp proxy",
        "trainer_started_at": trainer_started.isoformat() if trainer_started else None,
        "trainer_started_at_f": 1 if trainer_started else 0,
        "trainer_started_at_source": "together.events.TRAINING_START" if ev_training_start else "together.started_at",
        "trainer_started_at_reason": None if trainer_started else "missing",
        "training_ended_at": training_ended.isoformat() if training_ended else None,
        "training_ended_at_f": 1 if ev_training_complete else (0 if updated else 0),
        "training_ended_at_source": "together.events.TRAINING_COMPLETE" if ev_training_complete else "together.updated_at_proxy",
        "training_ended_at_reason": None if ev_training_complete else "provider list payload lacks explicit training_end",
        "wall_time_min": wall,
        "wall_time_min_f": 1 if wall is not None else 0,
        "wall_time_min_source": "derived(created_at,model_available_at)",
        "wall_time_min_reason": None if wall is not None else "missing timestamps",
        "training_time_min": training,
        "training_time_min_f": 1 if training is not None else 0,
        "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
        "training_time_min_reason": None if training is not None else "missing timestamps",
        "benchmark_timing_eligible": bool(wall is not None and training is not None),
        "benchmark_timing_eligible_reason": "requires wall_time and training_time",
        "source_system": "together_api",
        "ingest_run_id": ingest_run_id,
    }


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), default=str))
            f.write("\n")
            count += 1
    return count


def _bq_load_and_merge(
    cfg: BqConfig,
    target_table: str,
    jsonl_path: Path,
    merge_sql: str,
) -> None:
    temp_table = f"{target_table}__staging_{uuid.uuid4().hex[:10]}"
    _bq_query(cfg, f"CREATE TABLE `{cfg.project}.{temp_table}` LIKE `{cfg.project}.{target_table}`;")
    try:
        _run([
            "bq",
            "--project_id",
            cfg.project,
            "--location",
            cfg.location,
            "load",
            "--source_format=NEWLINE_DELIMITED_JSON",
            f"{cfg.project}:{temp_table}",
            str(jsonl_path),
        ])
        _bq_query(cfg, merge_sql.replace("__TEMP__", f"`{cfg.project}.{temp_table}`"))
    finally:
        _bq_query(cfg, f"DROP TABLE `{cfg.project}.{temp_table}`;")


def _merge_sql_raw(project: str) -> str:
    return f"""
MERGE `{project}.{RAW_TABLE}` T
USING __TEMP__ S
ON T.provider = S.provider
AND T.provider_run_id = S.provider_run_id
AND T.payload_sha256 = S.payload_sha256
WHEN NOT MATCHED THEN INSERT ROW
""".strip()


def _merge_sql_replace(project: str, table: str, key_cols: List[str], cols: List[str]) -> str:
    on_clause = " AND ".join([f"T.{c}=S.{c}" for c in key_cols])
    set_clause = ",\n  ".join([f"{c}=S.{c}" for c in cols if c not in key_cols])
    col_list = ", ".join(cols)
    val_list = ", ".join([f"S.{c}" for c in cols])
    return f"""
MERGE `{project}.{table}` T
USING __TEMP__ S
ON {on_clause}
WHEN MATCHED THEN UPDATE SET
  {set_clause}
WHEN NOT MATCHED THEN INSERT ({col_list}) VALUES ({val_list})
""".strip()


def _get_secret(name: str, project: str) -> str:
    out = _run([
        "gcloud",
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret",
        name,
        "--project",
        project,
    ])
    return out.strip()


def _run_post_load_dq(cfg: BqConfig) -> None:
    checks = {
        "raw_event_date_nulls": f"SELECT COUNT(*) FROM `{cfg.project}.{RAW_TABLE}` WHERE event_date IS NULL",
        "raw_redaction_false": f"SELECT COUNT(*) FROM `{cfg.project}.{RAW_TABLE}` WHERE redaction_applied IS NOT TRUE OR redaction_scan_passed IS NOT TRUE",
        "raw_secret_pattern_hits": (
            f"SELECT COUNT(*) FROM `{cfg.project}.{RAW_TABLE}` "
            "WHERE REGEXP_CONTAINS(TO_JSON_STRING(payload_redacted), r'(?i)Bearer\\s+[A-Za-z0-9._-]+') "
            "OR REGEXP_CONTAINS(TO_JSON_STRING(payload_redacted), r'(?i)X-Goog-Signature=') "
            "OR REGEXP_CONTAINS(TO_JSON_STRING(payload_redacted), r'(?i)\\bhf_[A-Za-z0-9]{20,}\\b') "
            "OR REGEXP_CONTAINS(TO_JSON_STRING(payload_redacted), r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}')"
        ),
        "timing_negative_values": f"SELECT COUNT(*) FROM `{cfg.project}.{TIME_TABLE}` WHERE wall_time_min < 0 OR training_time_min < 0",
        "raw_duplicate_keys": (
            f"SELECT COUNT(*) FROM ("
            f"SELECT provider, provider_run_id, payload_sha256 "
            f"FROM `{cfg.project}.{RAW_TABLE}` "
            f"GROUP BY provider, provider_run_id, payload_sha256 "
            f"HAVING COUNT(*) > 1)"
        ),
        "conditions_duplicate_keys": (
            f"SELECT COUNT(*) FROM ("
            f"SELECT provider, workload_id, workload_type, as_of_ts "
            f"FROM `{cfg.project}.{COND_TABLE}` "
            f"GROUP BY provider, workload_id, workload_type, as_of_ts "
            f"HAVING COUNT(*) > 1)"
        ),
        "timing_duplicate_keys": (
            f"SELECT COUNT(*) FROM ("
            f"SELECT provider, workload_id, workload_type, as_of_ts "
            f"FROM `{cfg.project}.{TIME_TABLE}` "
            f"GROUP BY provider, workload_id, workload_type, as_of_ts "
            f"HAVING COUNT(*) > 1)"
        ),
    }

    failures: List[str] = []
    for name, sql in checks.items():
        c = _bq_scalar_int(cfg, sql)
        if c > 0:
            failures.append(f"{name}={c}")

    if failures:
        raise RuntimeError("post-load DQ checks failed: " + ", ".join(failures))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Populate benchmark v1 BigQuery tables from available sources.")
    p.add_argument("--project", default=os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "inbound-dahlia-507808-g1")
    p.add_argument("--location", default=os.getenv("BQ_LOCATION", "EU"))
    p.add_argument("--together-local-json", default="outputs/odyn_together_warn_v4/raw/fine_tuning_list_pages.json")
    p.add_argument("--together-events-glob", default="outputs/odyn_together_warn_v4/raw/fine_tuning_job_ft-*.events.raw.json")
    p.add_argument("--eks-csv", default="outputs/eks_kuberay_job_map.csv")
    p.add_argument("--prefer-live-together", action="store_true")
    p.add_argument("--max-pages", type=int, default=20)
    p.add_argument("--timeout-seconds", type=int, default=60)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = BqConfig(project=args.project, location=args.location)

    fetched_at = datetime.now(UTC)
    ingest_run_id = f"bq_ingest_v1_{fetched_at.strftime('%Y%m%dT%H%M%SZ')}"
    hmac_key = _get_secret("benchmark-redaction-hmac-key", args.project)

    together_rows: List[Dict[str, Any]] = []
    if args.prefer_live_together:
        try:
            together_rows = _fetch_together_rows_live(max_pages=args.max_pages, timeout_seconds=args.timeout_seconds)
        except Exception:
            together_rows = []
    if not together_rows:
        local_path = Path(args.together_local_json)
        if local_path.exists():
            together_rows = _load_together_rows_from_local(local_path)

    eks_path = Path(args.eks_csv)
    if not eks_path.exists():
        desktop_candidate = Path("/Users/michaelsigamani/Desktop/kuberay_jobs_sep01_to_now.csv")
        if desktop_candidate.exists():
            eks_path = desktop_candidate
    eks_rows = _load_eks_rows(eks_path)
    together_events_map = _load_together_events_map(args.together_events_glob)

    raw_rows: List[Dict[str, Any]] = []
    cond_rows: List[Dict[str, Any]] = []
    time_rows: List[Dict[str, Any]] = []

    for row in together_rows:
        raw_rows.append(_raw_row_from_together(row, ingest_run_id, fetched_at, hmac_key, together_events_map))
        cond_rows.append(_conditions_from_together(row, ingest_run_id, fetched_at))
        time_rows.append(_timing_from_together(row, ingest_run_id, fetched_at, together_events_map))

    for row in eks_rows:
        raw_rows.append(_raw_row_from_eks(row, ingest_run_id, fetched_at, hmac_key))
        cond_rows.append(_conditions_from_eks(row, ingest_run_id, fetched_at))

    if args.dry_run:
        print(json.dumps({
            "ingest_run_id": ingest_run_id,
            "together_rows": len(together_rows),
            "eks_rows": len(eks_rows),
            "raw_rows": len(raw_rows),
            "conditions_rows": len(cond_rows),
            "timing_rows": len(time_rows),
        }, indent=2))
        return

    with tempfile.TemporaryDirectory(prefix="bq_ingest_v1_") as td:
        tdir = Path(td)
        raw_path = tdir / "raw.jsonl"
        cond_path = tdir / "conditions.jsonl"
        time_path = tdir / "timing.jsonl"
        _write_jsonl(raw_path, raw_rows)
        _write_jsonl(cond_path, cond_rows)
        _write_jsonl(time_path, time_rows)

        if raw_rows:
            _bq_load_and_merge(cfg, RAW_TABLE, raw_path, _merge_sql_raw(args.project))

        cond_cols = [
            "as_of_ts", "provider", "workload_id", "workload_type", "provider_run_id", "is_benchmark_run", "is_customer_workload",
            "model_id", "model_id_f", "model_id_source", "model_id_reason",
            "training_objective", "training_objective_f", "training_objective_source", "training_objective_reason",
            "training_method", "training_method_f", "training_method_source", "training_method_reason",
            "lora_rank", "lora_rank_f", "lora_rank_source", "lora_rank_reason",
            "lora_alpha", "lora_alpha_f", "lora_alpha_source", "lora_alpha_reason",
            "batch_size_value", "batch_size_raw", "batch_size_kind", "batch_size_f", "batch_size_source", "batch_size_reason",
            "learning_rate", "learning_rate_f", "learning_rate_source", "learning_rate_reason",
            "seq_len", "seq_len_f", "seq_len_source", "seq_len_reason",
            "gpu_count", "gpu_count_f", "gpu_count_source", "gpu_count_reason",
            "precision", "precision_f", "precision_source", "precision_reason",
            "dataset_uri_sanitized", "dataset_uri_sanitized_f", "dataset_uri_sanitized_source", "dataset_uri_sanitized_reason",
            "dataset_content_hash", "dataset_content_hash_f", "dataset_content_hash_source", "dataset_content_hash_reason",
            "dataset_identity_hmac", "dataset_identity_hmac_f", "dataset_identity_hmac_source", "dataset_identity_hmac_reason", "dataset_identity_hmac_key_version",
            "tokenizer_id", "tokenizer_id_f", "tokenizer_id_source", "tokenizer_id_reason",
            "tokenizer_fallback_used", "tokenizer_fallback_used_f", "tokenizer_fallback_reason",
            "source_system", "source_record_ref", "ingest_run_id",
        ]
        if cond_rows:
            _bq_load_and_merge(
                cfg,
                COND_TABLE,
                cond_path,
                _merge_sql_replace(args.project, COND_TABLE, ["provider", "workload_id", "workload_type", "as_of_ts"], cond_cols),
            )

        time_cols = [
            "as_of_ts", "provider", "workload_id", "workload_type",
            "submitted_at", "submitted_at_f", "submitted_at_source", "submitted_at_reason",
            "model_available_at", "model_available_at_f", "model_available_at_source", "model_available_at_reason",
            "trainer_started_at", "trainer_started_at_f", "trainer_started_at_source", "trainer_started_at_reason",
            "training_ended_at", "training_ended_at_f", "training_ended_at_source", "training_ended_at_reason",
            "wall_time_min", "wall_time_min_f", "wall_time_min_source", "wall_time_min_reason",
            "training_time_min", "training_time_min_f", "training_time_min_source", "training_time_min_reason",
            "benchmark_timing_eligible", "benchmark_timing_eligible_reason",
            "source_system", "ingest_run_id",
        ]
        if time_rows:
            _bq_load_and_merge(
                cfg,
                TIME_TABLE,
                time_path,
                _merge_sql_replace(args.project, TIME_TABLE, ["provider", "workload_id", "workload_type", "as_of_ts"], time_cols),
            )

    _run_post_load_dq(cfg)

    print(json.dumps({
        "status": "ok",
        "ingest_run_id": ingest_run_id,
        "ingested": {
            "raw": len(raw_rows),
            "conditions": len(cond_rows),
            "timing": len(time_rows),
            "together_source_rows": len(together_rows),
            "eks_source_rows": len(eks_rows),
        },
        "timestamp": _now_iso(),
    }, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import contextlib
import dataclasses
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

try:
    from google.cloud import storage
except Exception:  # pragma: no cover
    storage = None


SCHEMA_VERSION = "pg_state_snapshot_v1"
REDACTION_VERSION = "extractor_v0_redact_2026_10_11"
MAX_TEXT_BYTES = 4096
TRUNCATION_MARKER = "...[TRUNCATED]"
EXIT_OK = 0
EXIT_ALERT = 20
EXIT_ERROR = 1
FREE_TEXT_FIELDS = {"error_message", "error_summary", "failure_reason"}
FORBIDDEN_JSON_COLUMNS = {
    "inventory_snapshot_json",
    "workload_json",
    "provider_errors_json",
    "training_config",
}
ALLOWLISTED_JSON_COLUMNS = {"accepted_recommendation_json", "response_json"}
DENYLIST_EXACT = {"hf_token", "password_hash", "email", "training_config"}
GPU_ID_SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_.:/-]+$")


SCAN_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    (
        "private_or_loopback_ip",
        re.compile(
            r"\b(?:"
            r"10(?:\.\d{1,3}){3}|"
            r"127(?:\.\d{1,3}){3}|"
            r"192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
            r")\b"
        ),
    ),
    ("internal_host", re.compile(r"(?i)\b[\w.-]+\.(?:internal|ts\.net|svc\.cluster\.local)\b")),
    ("aws_arn", re.compile(r"(?i)arn:aws:")),
    ("example_invalid_domain", re.compile(r"(?i)@example\.invalid\b")),
    (
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----", re.IGNORECASE),
    ),
    ("private_key_literal", re.compile(r"(?i)\bBEGIN PRIVATE KEY\b")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("hex_40_plus", re.compile(r"\b[a-fA-F0-9]{40,}\b")),
    (
        "signed_url_param",
        re.compile(r"(?i)(?:[?&](?:x-amz-signature|x-goog-signature|signature|sig)=|x-amz-credential=)"),
    ),
    ("signed_url_literal", re.compile(r"(?i)\bX-Amz-(?:Signature|Credential)\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]+=*")),
    ("hf_token", re.compile(r"(?i)\bhf_[A-Za-z0-9]{4,}\b")),
    ("fake_literal", re.compile(r"\bFAKEFAKEFAKE\b")),
    ("customer_secret_literal", re.compile(r"(?i)\bcustomer\s+secret\b")),
    ("other_supplier_literal", re.compile(r"(?i)\bother-supplier\b")),
    ("supplier_host_literal", re.compile(r"(?i)\bsupplier-host-\d+\b")),
]

URL_PATTERN = re.compile(r"https?://[^\\s'\"<>]+")


@dataclasses.dataclass
class ExtractorConfig:
    pg_dsn_env: str
    pg_database: str
    sslmode: str
    sslmode_explicit: bool
    pg_password_secret_name: str
    pg_password_secret_region: str
    gcs_bucket: str
    gcs_prefix: str
    kms_hmac_key_arn: str
    hmac_key_version: str
    tables: List[Dict[str, Any]]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extractor v0: sanitized Postgres state snapshots")
    p.add_argument("--config", required=True, help="Path to extractor config JSON")
    p.add_argument("--since", default=None, help="Deprecated; ignored for change-only snapshots")
    p.add_argument("--limit-per-table", type=int, default=5000)
    p.add_argument("--dry-run", action="store_true", help="Read/scan only. Print table summaries and do not write sink objects.")
    p.add_argument("--canary", action="store_true", help="Write only _canary/<run_id>.json through the GCS sink.")
    return p.parse_args()


def load_config(path: Path) -> ExtractorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sslmode_explicit = "sslmode" in raw
    sslmode = str(raw.get("sslmode", "require")).strip().lower()
    if sslmode not in {"require", "prefer"}:
        raise RuntimeError("sslmode must be either 'require' or 'prefer'")
    if sslmode == "prefer" and not sslmode_explicit:
        raise RuntimeError("sslmode=prefer must be set explicitly in config")
    return ExtractorConfig(
        pg_dsn_env=str(raw["pg_dsn_env"]),
        pg_database=str(raw.get("pg_database", "marketplace")),
        sslmode=sslmode,
        sslmode_explicit=sslmode_explicit,
        pg_password_secret_name=str(raw.get("pg_password_secret_name", "odyn/ingest-ro-db")),
        pg_password_secret_region=str(raw.get("pg_password_secret_region", "us-west-2")),
        gcs_bucket=str(raw["gcs_bucket"]),
        gcs_prefix=str(raw.get("gcs_prefix", "pg")).strip("/"),
        kms_hmac_key_arn=str(raw["kms_hmac_key_arn"]),
        hmac_key_version=str(raw.get("hmac_key_version", "kms-hmac-v1")),
        tables=list(raw["tables"]),
    )


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def format_rfc3339_utc_microseconds(value: dt.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    value = value.astimezone(dt.timezone.utc)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dt.datetime):
        return format_rfc3339_utc_microseconds(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_uri(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not s:
        return value
    parsed = urlsplit(s)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def sanitize_urls_in_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        return sanitize_uri(token) or token

    return URL_PATTERN.sub(repl, text)


def truncate_utf8_with_marker(text: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    payload_budget = max(0, max_bytes - len(marker_bytes))
    trimmed = encoded[:payload_budget].decode("utf-8", errors="ignore")
    return trimmed + TRUNCATION_MARKER


def kms_key_id_from_arn(kms_key_arn: str) -> str:
    arn = (kms_key_arn or "").strip()
    m = re.match(r"^arn:aws:kms:[^:]+:\d{12}:(key|alias)/(.+)$", arn)
    if not m:
        raise RuntimeError("kms_hmac_key_arn is not a valid KMS key/alias ARN")
    return f"{m.group(1)}/{m.group(2)}"


def normalize_hmac_input(column_name: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return ""
    col = (column_name or "").lower()
    if col == "id" or col.endswith("_id"):
        return s.lower()
    return s


def kms_hmac_hex(kms_client: Any, key_id: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if kms_client is None:
        raise RuntimeError("KMS client unavailable; extractor requires GenerateMac capability")
    out = kms_client.generate_mac(KeyId=key_id, Message=value.encode("utf-8"), MacAlgorithm="HMAC_SHA_256")
    return base64.b16encode(out["Mac"]).decode("ascii").lower()


def to_rfc3339_utc(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return format_rfc3339_utc_microseconds(value)
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day, tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return None


def serialize_scalar(db_type: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    t = (db_type or "").lower()
    ts = to_rfc3339_utc(value)
    if ts is not None and ("timestamp" in t or isinstance(value, (dt.datetime, dt.date))):
        return ts
    if t in {"smallint", "integer", "bigint", "numeric", "decimal", "real", "double precision"}:
        return str(value)
    if "uuid" in t:
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    return value


def is_denied_column(column_name: str) -> bool:
    c = column_name.strip().lower()
    if c in DENYLIST_EXACT:
        return True
    if "token_hash" in c:
        return True
    if c.startswith("api_key"):
        return True
    if c.startswith("ssh_"):
        return True
    return False


def _safe_array_of_strings(
    value: Any,
    *,
    finding_prefix: str,
    findings: List[Dict[str, str]],
    table_name: str,
    row_pk: str,
    field: str,
) -> Tuple[List[str], int]:
    out: List[str] = []
    dropped = 0
    if not isinstance(value, list):
        findings.append({"pattern": f"{finding_prefix}_type", "table": table_name, "row_pk": row_pk, "field": field})
        return out, 0
    for item in value:
        if isinstance(item, str) and GPU_ID_SAFE_PATTERN.match(item):
            out.append(item)
        else:
            findings.append({"pattern": f"{finding_prefix}_element", "table": table_name, "row_pk": row_pk, "field": field})
            dropped += 1
    return out, dropped


def _sanitize_accepted_recommendation_json(
    value: Any,
    findings: List[Dict[str, str]],
    table_name: str,
    row_pk: str,
    field: str,
) -> Tuple[Optional[Dict[str, Any]], int, int]:
    if not isinstance(value, dict):
        findings.append({"pattern": "accepted_recommendation_json_type", "table": table_name, "row_pk": row_pk, "field": field})
        return None, 0, 0

    allowed_keys = {
        "candidate_id",
        "machine_id",
        "provider",
        "rank",
        "reservation_expires_at",
        "reservation_id",
        "source",
        "selected_placement",
        "pricing",
        "specs",
    }
    out: Dict[str, Any] = {}
    dropped_keys = len(set(value.keys()) - allowed_keys)
    dropped_array_elements = 0
    for k in allowed_keys:
        if k in value:
            out[k] = value[k]

    selected = out.get("selected_placement")
    if selected is not None:
        if isinstance(selected, dict):
            cleaned: Dict[str, Any] = {}
            if "node_id" in selected:
                if isinstance(selected["node_id"], str):
                    cleaned["node_id"] = selected["node_id"]
                else:
                    findings.append({"pattern": "selected_placement.node_id_type", "table": table_name, "row_pk": row_pk, "field": field})
            if "gpu_ids" in selected:
                cleaned_vals, dropped = _safe_array_of_strings(
                    selected["gpu_ids"],
                    finding_prefix="selected_placement.gpu_ids",
                    findings=findings,
                    table_name=table_name,
                    row_pk=row_pk,
                    field=field,
                )
                cleaned["gpu_ids"] = cleaned_vals
                dropped_array_elements += dropped
            out["selected_placement"] = cleaned
        else:
            findings.append({"pattern": "selected_placement_type", "table": table_name, "row_pk": row_pk, "field": field})
            out.pop("selected_placement", None)
            dropped_keys += 1

    pricing = out.get("pricing")
    if pricing is not None:
        if isinstance(pricing, dict) and "cost_per_hour_usd" in pricing:
            v = pricing["cost_per_hour_usd"]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out["pricing"] = {"cost_per_hour_usd": v}
            else:
                findings.append({"pattern": "pricing.cost_per_hour_usd_type", "table": table_name, "row_pk": row_pk, "field": field})
                out.pop("pricing", None)
                dropped_keys += 1
        elif isinstance(pricing, dict):
            out["pricing"] = {}
        else:
            findings.append({"pattern": "pricing_type", "table": table_name, "row_pk": row_pk, "field": field})
            out.pop("pricing", None)
            dropped_keys += 1

    specs = out.get("specs")
    if specs is not None:
        if isinstance(specs, dict) and "gpu" in specs:
            gpu = specs["gpu"]
            if isinstance(gpu, (str, int, float, bool)) or gpu is None:
                out["specs"] = {"gpu": gpu}
            else:
                findings.append({"pattern": "specs.gpu_type", "table": table_name, "row_pk": row_pk, "field": field})
                out.pop("specs", None)
                dropped_keys += 1
        elif isinstance(specs, dict):
            out["specs"] = {}
        else:
            findings.append({"pattern": "specs_type", "table": table_name, "row_pk": row_pk, "field": field})
            out.pop("specs", None)
            dropped_keys += 1

    return out, dropped_keys, dropped_array_elements


def _sanitize_response_json(
    value: Any,
    findings: List[Dict[str, str]],
    table_name: str,
    row_pk: str,
    field: str,
) -> Tuple[Optional[Dict[str, Any]], int, int]:
    if not isinstance(value, dict):
        findings.append({"pattern": "response_json_type", "table": table_name, "row_pk": row_pk, "field": field})
        return None, 0, 0
    allowed = {
        "admission_state",
        "next_label",
        "next_route",
        "queue_position",
        "resource_id",
        "route_type",
        "status",
    }
    kept = {k: value[k] for k in allowed if k in value}
    dropped_keys = len(set(value.keys()) - allowed)
    return kept, dropped_keys, 0


def sanitize_json_column(
    column: str,
    value: Any,
    findings: List[Dict[str, str]],
    table_name: str,
    row_pk: str,
) -> Tuple[Any, int, int]:
    if column == "accepted_recommendation_json":
        return _sanitize_accepted_recommendation_json(value, findings, table_name, row_pk, column)
    if column == "response_json":
        return _sanitize_response_json(value, findings, table_name, row_pk, column)
    return None, 0, 0


def scan_text_patterns(text: str) -> List[str]:
    hits: List[str] = []
    for name, pattern in SCAN_PATTERNS:
        if pattern.search(text):
            hits.append(name)
    return sorted(set(hits))


def mask_free_text(text: str) -> Tuple[str, List[str]]:
    masked = text
    findings: List[str] = []
    for name, pattern in SCAN_PATTERNS:
        if pattern.search(masked):
            findings.append(name)
            masked = pattern.sub("[REDACTED]", masked)
    return masked, sorted(set(findings))


def parse_pk(row: Mapping[str, Any], pk_cols: Sequence[str]) -> Dict[str, Any]:
    return {k: row.get(k) for k in pk_cols}


def transform_row(
    row: Dict[str, Any],
    column_types: Dict[str, str],
    table_cfg: Dict[str, Any],
    table_name: str,
    kms_client: Any,
    kms_key_id: str,
) -> Tuple[Dict[str, Any], List[Dict[str, str]], bool, Dict[str, Dict[str, int]]]:
    out: Dict[str, Any] = {}
    findings: List[Dict[str, str]] = []
    alert = False
    dropped_keys_by_col: Dict[str, int] = {}
    dropped_array_by_col: Dict[str, int] = {}
    pk_cols = list(table_cfg.get("pk_columns", []))
    row_pk_str = canonical_json(parse_pk(row, pk_cols))

    for col, raw_value in row.items():
        col_l = col.lower()
        db_type = column_types.get(col, "")

        if col_l in FORBIDDEN_JSON_COLUMNS:
            continue

        value = raw_value
        if "json" in db_type.lower() and isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = None

        if col_l in {"gpu_identifiers", "node_ids"}:
            value, dropped = _safe_array_of_strings(
                value,
                finding_prefix=col_l,
                findings=findings,
                table_name=table_name,
                row_pk=row_pk_str,
                field=col,
            )
            if dropped:
                dropped_array_by_col[col] = dropped_array_by_col.get(col, 0) + dropped

        if col_l in ALLOWLISTED_JSON_COLUMNS:
            value, dropped_keys, dropped_array = sanitize_json_column(col_l, value, findings, table_name, row_pk_str)
            if dropped_keys:
                dropped_keys_by_col[col] = dropped_keys_by_col.get(col, 0) + dropped_keys
            if dropped_array:
                dropped_array_by_col[col] = dropped_array_by_col.get(col, 0) + dropped_array

        if isinstance(value, str):
            if col_l in FREE_TEXT_FIELDS:
                value = sanitize_urls_in_text(value)
                value, free_text_hits = mask_free_text(value)
                value = truncate_utf8_with_marker(value)
                for hit in free_text_hits:
                    findings.append({"pattern": hit, "table": table_name, "row_pk": row_pk_str, "field": col})
                    alert = True
            else:
                value = sanitize_uri(value) or value
                hits = scan_text_patterns(value)
                if hits:
                    hit = hits[0]
                    raise RuntimeError(
                        f"structured scan finding pattern={hit} table={table_name} row_pk={row_pk_str} field={col}"
                    )

        if col in set(table_cfg.get("hmac_fields", [])):
            sanitized_for_hmac = value
            if isinstance(sanitized_for_hmac, str):
                sanitized_for_hmac = sanitize_uri(sanitized_for_hmac) or sanitized_for_hmac
            hmac_input = normalize_hmac_input(col, sanitized_for_hmac)
            value = kms_hmac_hex(kms_client, kms_key_id, hmac_input)

        out[col] = serialize_scalar(db_type, value)

    return out, findings, alert, {
        "dropped_keys": dropped_keys_by_col,
        "dropped_array_elements": dropped_array_by_col,
    }


def _resolve_pg_password(config: ExtractorConfig) -> Optional[str]:
    env_password = os.getenv("PGPASSWORD")
    if env_password:
        return env_password
    if boto3 is None:
        return None
    profile = os.getenv("AWS_PROFILE")
    session = boto3.session.Session(profile_name=profile) if profile else boto3.session.Session()
    sm = session.client("secretsmanager", region_name=config.pg_password_secret_region)
    secret = sm.get_secret_value(SecretId=config.pg_password_secret_name)
    raw = secret.get("SecretString")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            for key in ["password", "pg_password", "PGPASSWORD", "value"]:
                if key in payload and payload[key]:
                    return str(payload[key])
    except Exception:
        return str(raw)
    return None


def _effective_sslmode(config: ExtractorConfig) -> str:
    mode = (config.sslmode or "require").strip().lower()
    if mode == "prefer" and not config.sslmode_explicit:
        raise RuntimeError("sslmode=prefer is only allowed when explicitly set in config")
    if mode not in {"require", "prefer"}:
        raise RuntimeError("unsupported sslmode; expected require or prefer")
    return mode


def pg_connect_from_env(config: ExtractorConfig):
    if psycopg is None:
        raise RuntimeError("psycopg is not installed")
    dsn = (os.getenv(config.pg_dsn_env) or "").strip()
    if not dsn:
        raise RuntimeError(f"missing required env var: {config.pg_dsn_env}")

    password = _resolve_pg_password(config)
    kwargs: Dict[str, Any] = {
        "dbname": config.pg_database,
        "sslmode": _effective_sslmode(config),
    }
    if password:
        kwargs["password"] = password
    conninfo = psycopg.conninfo.make_conninfo(dsn, **kwargs)
    return psycopg.connect(conninfo)


def fetch_table_columns(conn: Any, schema: str, table: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              c.column_name,
              c.data_type,
              c.ordinal_position,
              has_column_privilege(current_user, c.table_schema || '.' || c.table_name, c.column_name, 'SELECT') AS has_select
            FROM information_schema.columns c
            WHERE c.table_schema = %s
              AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (schema, table),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for column_name, data_type, ordinal_position, has_select in rows:
        out.append(
            {
                "column_name": str(column_name),
                "data_type": str(data_type),
                "ordinal_position": int(ordinal_position),
                "has_select": bool(has_select),
            }
        )
    return out


def assert_config_matches_grants(conn: Any, table_cfg: Dict[str, Any]) -> Tuple[List[str], Dict[str, str]]:
    schema = table_cfg["schema"]
    table = table_cfg["table"]
    full = f"{schema}.{table}"

    configured_columns = list(table_cfg.get("columns") or [])
    if not configured_columns:
        raise RuntimeError(f"{full} requires explicit columns generated from grants")

    rows = fetch_table_columns(conn, schema, table)
    granted = [r["column_name"] for r in rows if r["has_select"]]
    granted_set = set(granted)
    configured_set = set(configured_columns)

    only_in_config = sorted(configured_set - granted_set)
    only_in_grants = sorted(granted_set - configured_set)
    if only_in_config or only_in_grants:
        raise RuntimeError(
            f"{full} config/grants mismatch only_in_config={only_in_config} only_in_grants={only_in_grants}"
        )

    json_allowlists = set((table_cfg.get("json_allowlists") or {}).keys())
    type_by_col = {r["column_name"]: r["data_type"] for r in rows}
    for col in configured_columns:
        if not has_column_select_privilege(conn, schema, table, col):
            raise RuntimeError(f"{full} has_column_privilege denied for column={col}")
        if is_denied_column(col):
            raise RuntimeError(f"{full} selected columns include deny-listed field {col}")
        col_type = type_by_col.get(col, "").lower()
        if col.lower() in FORBIDDEN_JSON_COLUMNS:
            raise RuntimeError(f"{full} selected columns include forbidden JSON field {col}")
        if col_type in {"json", "jsonb"} and col.lower() not in json_allowlists and col.lower() not in {"gpu_identifiers", "node_ids"}:
            raise RuntimeError(f"{full} json/jsonb column not in json_allowlists: {col}")

    selected_types = {col: type_by_col[col] for col in configured_columns}
    return configured_columns, selected_types


def has_column_select_privilege(conn: Any, schema: str, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT has_column_privilege(current_user, %s || '.' || %s, %s, 'SELECT')
            """,
            (schema, table, column),
        )
        row = cur.fetchone()
    return bool(row[0])


def begin_readonly_repeatable_read(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")


def fetch_table_count(conn: Any, schema: str, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {schema}.{table}")
        row = cur.fetchone()
    return int(row[0])


def fetch_rows(conn: Any, schema: str, table: str, columns: Sequence[str], pk_columns: Sequence[str], limit: int) -> List[Dict[str, Any]]:
    order_by = ", ".join(pk_columns)
    sql = f"SELECT {', '.join(columns)} FROM {schema}.{table} ORDER BY {order_by} LIMIT {int(limit) + 1}"
    with conn.cursor() as cur:
        cur.execute(sql)
        colnames = [d.name for d in cur.description]
        recs = cur.fetchall()
    return [dict(zip(colnames, rec)) for rec in recs]


class LocalDirectorySink:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.write_order: List[str] = []

    def put_once(self, key: str, body: bytes, content_type: str) -> None:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as fp:
            fp.write(body)
        self.write_order.append(key)


class GcsSink:
    def __init__(self, bucket: str, *, storage_client: Any = None):
        if storage is None and storage_client is None:
            raise RuntimeError("google-cloud-storage is unavailable")
        self.bucket = bucket
        self.storage_client = storage_client or storage.Client()
        self.write_order: List[str] = []

    def put_once(self, key: str, body: bytes, content_type: str) -> None:
        blob = self.storage_client.bucket(self.bucket).blob(key)
        blob.upload_from_string(body, content_type=content_type, if_generation_match=0)
        self.write_order.append(key)


class JsonStateStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, table_name: str) -> Path:
        safe = table_name.replace("/", "_")
        return self.root / f"{safe}.state.json"

    def load(self, table_name: str) -> Optional[Dict[str, str]]:
        p = self._path(table_name)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def save(self, table_name: str, mapping: Dict[str, str]) -> None:
        p = self._path(table_name)
        p.write_text(canonical_json(mapping), encoding="utf-8")

    def _alerts_path(self) -> Path:
        return self.root / "_alert_fingerprints.json"

    def load_alert_fingerprints(self) -> set[str]:
        p = self._alerts_path()
        if not p.exists():
            return set()
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return set()
        return {str(x) for x in raw}

    def save_alert_fingerprints(self, values: set[str]) -> None:
        p = self._alerts_path()
        p.write_text(canonical_json(sorted(values)), encoding="utf-8")


def _table_output_prefix(gcs_prefix: str, table_name: str, captured_date: str, run_id: str) -> str:
    prefix = gcs_prefix.strip("/")
    return f"{prefix}/v1/table={table_name}/dt={captured_date}/run={run_id}"


def _build_record(
    *,
    snapshot_id: str,
    captured_at: str,
    captured_date: str,
    table_name: str,
    row_pk_str: str,
    row_hash: str,
    is_deleted: bool,
    row_json: Any,
    ingest_run_id: str,
    hmac_key_id: str,
    source_row_count: int,
) -> Dict[str, Any]:
    return {
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "captured_date": captured_date,
        "table_name": table_name,
        "row_pk": row_pk_str,
        "row_hash": row_hash,
        "is_deleted": bool(is_deleted),
        "row_json": row_json,
        "redaction_version": REDACTION_VERSION,
        "ingest_run_id": ingest_run_id,
        "hmac_key_id": hmac_key_id,
        "source_row_count": int(source_row_count),
    }


def _diff_change_only(
    table_name: str,
    current_records: List[Dict[str, Any]],
    prior_state: Optional[Dict[str, str]],
) -> List[Dict[str, Any]]:
    if prior_state is None:
        return current_records

    current_map = {r["row_pk"]: r["row_hash"] for r in current_records}
    out: List[Dict[str, Any]] = []

    for rec in current_records:
        prev_hash = prior_state.get(rec["row_pk"])
        if prev_hash != rec["row_hash"]:
            out.append(rec)

    disappeared = sorted(set(prior_state.keys()) - set(current_map.keys()))
    for row_pk in disappeared:
        out.append(
            {
                "row_pk": row_pk,
                "row_hash": sha256_text("null"),
                "is_deleted": True,
                "row_json": None,
                "_table": table_name,
            }
        )
    return out


def run(
    config: ExtractorConfig,
    since: Optional[str],
    limit_per_table: int,
    *,
    kms_client: Any = None,
    sink: Any = None,
    state_store: Optional[JsonStateStore] = None,
    conn: Any = None,
    ingest_run_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    _ = since
    owned_conn = conn is None
    conn = conn or pg_connect_from_env(config)

    if sink is None:
        sink = GcsSink(config.gcs_bucket)

    if kms_client is None:
        kms_client = boto3.client("kms") if boto3 else None

    if state_store is None:
        state_store = JsonStateStore(Path(".pg_state_store"))

    hmac_key_id = kms_key_id_from_arn(config.kms_hmac_key_arn)
    captured_dt = utc_now()
    captured_at = format_rfc3339_utc_microseconds(captured_dt)
    captured_date = captured_dt.date().isoformat()
    run_id = ingest_run_id or f"extractor_v0_{captured_dt.strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex[:10]}"

    table_manifests: List[Dict[str, Any]] = []
    overall_findings: List[Dict[str, str]] = []
    alert = False
    tx_settings: Dict[str, str] = {}
    seen_alert_fingerprints = state_store.load_alert_fingerprints()
    ssl_status: Dict[str, Any] = {}

    try:
        begin_readonly_repeatable_read(conn)
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_isolation")
            isolation = str(cur.fetchone()[0])
            cur.execute("SHOW transaction_read_only")
            read_only = str(cur.fetchone()[0])
            tx_settings = {
                "transaction_isolation": isolation,
                "transaction_read_only": read_only,
            }

        ssl_status = _read_connection_ssl_status(conn)
        effective_sslmode = _effective_sslmode(config)
        if effective_sslmode == "require" and not ssl_status.get("encrypted", False):
            raise RuntimeError("sslmode=require but backend connection is not encrypted")

        for t in config.tables:
            schema = t["schema"]
            table = t["table"]
            table_name = f"{schema}.{table}"
            pk_columns = list(t.get("pk_columns") or [])
            if not pk_columns:
                raise RuntimeError(f"{table_name} missing pk_columns")

            selected_columns, selected_types = assert_config_matches_grants(conn, t)
            source_row_count = fetch_table_count(conn, schema, table)
            fetched_rows = fetch_rows(conn, schema, table, selected_columns, pk_columns, limit_per_table)

            if len(fetched_rows) > limit_per_table:
                raise RuntimeError(f"{table_name} row limit hit limit_per_table={limit_per_table}")
            if len(fetched_rows) != source_row_count:
                raise RuntimeError(
                    f"{table_name} row count mismatch rows_fetched={len(fetched_rows)} source_row_count={source_row_count}"
                )

            transformed_records: List[Dict[str, Any]] = []
            current_state_map: Dict[str, str] = {}
            table_dropped_keys: Dict[str, int] = {}
            table_dropped_array: Dict[str, int] = {}

            for row in fetched_rows:
                transformed_row, row_findings, _row_alert, row_drop_stats = transform_row(
                    row,
                    selected_types,
                    t,
                    table_name,
                    kms_client,
                    hmac_key_id,
                )
                for col, count in row_drop_stats["dropped_keys"].items():
                    table_dropped_keys[col] = table_dropped_keys.get(col, 0) + int(count)
                for col, count in row_drop_stats["dropped_array_elements"].items():
                    table_dropped_array[col] = table_dropped_array.get(col, 0) + int(count)

                pk = parse_pk(transformed_row, pk_columns)
                row_pk_str = canonical_json(pk)
                row_hash = sha256_text(canonical_json(transformed_row))
                current_state_map[row_pk_str] = row_hash

                for finding in row_findings:
                    fp = canonical_json(
                        {
                            "table": finding.get("table"),
                            "row_pk": finding.get("row_pk"),
                            "field": finding.get("field"),
                            "pattern": finding.get("pattern"),
                            "row_hash": row_hash,
                        }
                    )
                    if fp not in seen_alert_fingerprints:
                        seen_alert_fingerprints.add(fp)
                        overall_findings.append(finding)
                        alert = True

                transformed_records.append(
                    {
                        "row_pk": row_pk_str,
                        "row_hash": row_hash,
                        "is_deleted": False,
                        "row_json": transformed_row,
                    }
                )

            prior = state_store.load(table_name)
            cadence = str(t.get("cadence", "full_scan"))
            if cadence == "change_only":
                emit_rows = _diff_change_only(table_name, transformed_records, prior)
            else:
                emit_rows = transformed_records

            records = [
                _build_record(
                    snapshot_id=str(uuid.uuid4()),
                    captured_at=captured_at,
                    captured_date=captured_date,
                    table_name=table_name,
                    row_pk_str=item["row_pk"],
                    row_hash=item["row_hash"],
                    is_deleted=item["is_deleted"],
                    row_json=item["row_json"],
                    ingest_run_id=run_id,
                    hmac_key_id=hmac_key_id,
                    source_row_count=source_row_count,
                )
                for item in emit_rows
            ]

            prefix = _table_output_prefix(config.gcs_prefix, table_name, captured_date, run_id)
            data_key = f"{prefix}/part-0000.jsonl.gz"
            if not dry_run:
                payload = "\n".join(canonical_json(r) for r in records)
                if payload:
                    payload += "\n"
                compressed = gzip.compress(payload.encode("utf-8"))
                sink.put_once(data_key, compressed, "application/x-ndjson+gzip")

            if not dry_run:
                state_store.save(table_name, current_state_map)

            if dry_run:
                sample = records[0] if records else None
                row_findings_count = sum(1 for f in overall_findings if f.get("table") == table_name)
                print(f"TABLE {table_name}")
                print(f"  COLUMNS: {', '.join(selected_columns)}")
                print(f"  SOURCE_COUNT: {source_row_count}")
                print(f"  SAMPLE_REDACTED_ROW: {canonical_json(sample) if sample else 'null'}")
                print(f"  FINDINGS_COUNT: {row_findings_count}")
                print(f"  DROPPED_KEYS: {canonical_json(table_dropped_keys)}")
                print(f"  DROPPED_ARRAY_ELEMENTS: {canonical_json(table_dropped_array)}")

            table_manifests.append(
                {
                    "table_name": table_name,
                    "source_row_count": source_row_count,
                    "emitted_row_count": len(records),
                    "data_object": data_key,
                    "dropped_keys": table_dropped_keys,
                    "dropped_array_elements": table_dropped_array,
                }
            )

        with conn.cursor() as cur:
            cur.execute("COMMIT")

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "ingest_run_id": run_id,
            "captured_at": captured_at,
            "captured_date": captured_date,
            "hmac_key_id": hmac_key_id,
            "redaction_version": REDACTION_VERSION,
            "alert": alert,
            "findings_count": len(overall_findings),
            "finding_count": len(overall_findings),
            "findings": overall_findings,
            "transaction": tx_settings,
            "connection": {
                "effective_sslmode": effective_sslmode,
                "encrypted": bool(ssl_status.get("encrypted", False)),
                "ssl_version": str(ssl_status.get("version", "")),
                "ssl_cipher": str(ssl_status.get("cipher", "")),
            },
            "tables": table_manifests,
        }

        if not dry_run:
            # Manifest must be written last.
            for table_info in table_manifests:
                prefix = table_info["data_object"].rsplit("/", 1)[0]
                manifest_key = f"{prefix}/_manifest.json"
                sink.put_once(manifest_key, canonical_json(manifest).encode("utf-8"), "application/json")
            state_store.save_alert_fingerprints(seen_alert_fingerprints)

        if alert:
            print(f"ALERT run_id={run_id} findings_count={len(overall_findings)}", file=sys.stderr)
        print(
            "INFO effective_sslmode="
            f"{effective_sslmode} connection_encrypted={str(bool(ssl_status.get('encrypted', False))).lower()}"
            f" ssl_version={ssl_status.get('version', '')} ssl_cipher={ssl_status.get('cipher', '')}",
            file=sys.stderr,
        )

        return {
            "status": "ok",
            "ingest_run_id": run_id,
            "captured_at": captured_at,
            "alert": alert,
            "transaction": tx_settings,
            "findings_count": len(overall_findings),
            "finding_count": len(overall_findings),
            "connection": {
                "effective_sslmode": effective_sslmode,
                "encrypted": bool(ssl_status.get("encrypted", False)),
                "ssl_version": str(ssl_status.get("version", "")),
                "ssl_cipher": str(ssl_status.get("cipher", "")),
            },
            "tables": table_manifests,
            "sink_write_order": list(getattr(sink, "write_order", [])),
        }
    except Exception:
        try:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        if owned_conn:
            conn.close()


def validate_local_manifest_files(manifest: Dict[str, Any], sink_root: Path) -> None:
    root = Path(sink_root)
    tables = list(manifest.get("tables") or [])
    missing: List[str] = []
    for table in tables:
        obj = str(table.get("data_object") or "")
        if not obj:
            missing.append("<empty>")
            continue
        p = root / obj
        if not p.exists():
            missing.append(obj)
    if missing:
        raise RuntimeError(f"manifest references missing data objects: {missing}")


def _read_connection_ssl_status(conn: Any) -> Dict[str, Any]:
    """Read backend SSL status from pg_stat_ssl for the current session."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COALESCE(s.ssl, false) AS ssl,
              COALESCE(s.version, '') AS version,
              COALESCE(s.cipher, '') AS cipher
            FROM (SELECT pg_backend_pid() AS pid) p
            LEFT JOIN pg_stat_ssl s ON s.pid = p.pid
            """
        )
        row = cur.fetchone()
    if not row:
        return {"encrypted": False, "version": "", "cipher": ""}
    encrypted, version, cipher = row
    return {
        "encrypted": bool(encrypted),
        "version": str(version or ""),
        "cipher": str(cipher or ""),
    }


def run_canary(config: ExtractorConfig, *, sink: Any = None, run_id: Optional[str] = None) -> Dict[str, Any]:
    sink = sink or GcsSink(config.gcs_bucket)
    rid = run_id or f"canary_{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex[:8]}"
    key = f"_canary/{rid}.json"
    body = canonical_json({"run_id": rid, "captured_at": format_rfc3339_utc_microseconds(utc_now())}).encode("utf-8")
    sink.put_once(key, body, "application/json")
    return {"status": "ok", "run_id": rid, "object": key}


def exit_code_for_result(result: Dict[str, Any]) -> int:
    return EXIT_ALERT if bool(result.get("alert")) else EXIT_OK


def main() -> None:
    args = parse_args()
    cfg = load_config(Path(args.config))
    try:
        if args.canary:
            result = run_canary(cfg)
            print(json.dumps(result, indent=2))
            raise SystemExit(EXIT_OK)
        result = run(cfg, since=args.since, limit_per_table=args.limit_per_table, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        raise SystemExit(exit_code_for_result(result))
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR)


if __name__ == "__main__":
    main()

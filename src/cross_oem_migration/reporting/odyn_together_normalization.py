from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen


TOGETHER_PRICING_URL = "https://www.together.ai/pricing"
EXPECTED_TOKEN_COUNTS = {
    "qwen_1k": 287_860,
    "qwen_5k": 1_435_064,
    "qwen_10k": 2_854_762,
    "gpt_oss_5k": 1_672_237,
}


def round3(value: float | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_iso8601(ts: str | None) -> datetime | None:
    if not ts:
        return None
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def minutes_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start).total_seconds() / 60.0


def compute_serving_cost_per_million(tokens_per_second: float | None, dollars_per_hour: float | None, utilisation: float = 1.0) -> float | None:
    if not tokens_per_second or not dollars_per_hour or utilisation <= 0:
        return None
    baseline = dollars_per_hour / (tokens_per_second * 3600.0) * 1_000_000.0
    return baseline / utilisation


def compute_finetune_steady_cost_per_million(rate_per_hour: float | None, steady_tokens_per_second: float | None) -> float | None:
    if not rate_per_hour or not steady_tokens_per_second:
        return None
    return rate_per_hour / (steady_tokens_per_second * 3600.0) * 1_000_000.0


def compute_finetune_effective_cost_per_million(rate_per_hour: float | None, total_wall_minutes: float | None, tokens: int | None) -> float | None:
    if not rate_per_hour or not total_wall_minutes or not tokens:
        return None
    return (rate_per_hour * total_wall_minutes / 60.0) / (tokens / 1_000_000.0)


def expected_steps(tokens: int | None, batch_size: int | None, seq_len: int = 4096) -> int | None:
    if not tokens or not batch_size:
        return None
    return math.ceil(tokens / (batch_size * seq_len))


def token_delta(dataset_tokens: int | None, trained_tokens: int | None) -> int | None:
    if dataset_tokens is None or trained_tokens is None:
        return None
    return trained_tokens - dataset_tokens


def min_charge_binding(tokens: int | None, list_rate_per_million: float | None, minimum_charge: float | None) -> bool | None:
    if tokens is None or list_rate_per_million is None or minimum_charge is None:
        return None
    expected_billed = (tokens / 1_000_000.0) * list_rate_per_million
    return expected_billed < minimum_charge


def parse_together_price_units(total_price_raw: Any) -> float | None:
    value = safe_float(total_price_raw)
    if value is None:
        return None
    # Together API currently returns total_price as nano-USD integers.
    if value >= 1_000_000:
        return value / 1_000_000_000.0
    return value


def extract_fine_tune_pricing_table(pricing_markdown: str) -> list[dict[str, Any]]:
    lines = pricing_markdown.splitlines()
    tables: list[list[str]] = []
    capture: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            capture.append(stripped)
        elif capture:
            tables.append(capture)
            capture = []
    if capture:
        tables.append(capture)

    parsed_tables: list[list[dict[str, str]]] = []
    for table in tables:
        if len(table) < 3:
            continue
        header = [h.strip() for h in table[0].strip("|").split("|")]
        if "Model" not in header or "Supervised Fine-Tuning" not in header or "Minimum charge" not in header:
            continue
        rows: list[dict[str, str]] = []
        for raw in table[2:]:
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))
        if rows:
            parsed_tables.append(rows)

    model_to_rows: dict[str, list[dict[str, str]]] = {}
    for table_rows in parsed_tables:
        for row in table_rows:
            model_to_rows.setdefault(row["Model"], []).append(row)

    out: list[dict[str, Any]] = []
    for model, rows in sorted(model_to_rows.items()):
        first = rows[0]
        ambiguous = len(rows) > 1 and any(r != first for r in rows[1:])
        out.append(
            {
                "model": model,
                "lora_sft_usd_per_million": parse_usd_cell(first.get("Supervised Fine-Tuning", "")),
                "dpo_usd_per_million": parse_usd_cell(first.get("Direct Preference Optimization", "")),
                "minimum_charge_usd": parse_usd_cell(first.get("Minimum charge", "")),
                "pricing_table_ambiguous": ambiguous,
            }
        )
    return out


def parse_usd_cell(cell: str) -> float | None:
    m = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", cell or "")
    if not m:
        return None
    return float(m.group(1))


def extract_h100_on_demand_per_gpu_hour(pricing_markdown: str) -> float | None:
    for line in pricing_markdown.splitlines():
        if "NVIDIA HGX H100" in line and "$" in line:
            value = parse_usd_cell(line)
            if value is not None:
                return value
    return None


@dataclass
class TogetherCliResult:
    ok: bool
    command: list[str]
    stdout: str
    stderr: str
    json_value: Any | None


def run_together_cli_json(args: list[str], env: dict[str, str] | None = None) -> TogetherCliResult:
    effective_env = dict(os.environ)
    if env:
        effective_env.update(env)
    if not effective_env.get("TOGETHER_API_KEY") and effective_env.get("TOGETHERAI_API_KEY"):
        effective_env["TOGETHER_API_KEY"] = effective_env["TOGETHERAI_API_KEY"]
    exe = shutil.which("together") or shutil.which("tg")
    if not exe:
        return TogetherCliResult(
            ok=False,
            command=["together", *args, "--json"],
            stdout="",
            stderr="Together CLI not found in PATH",
            json_value=None,
        )
    cmd = [exe, *args, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=effective_env)
    parsed = None
    if proc.returncode == 0:
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None
    return TogetherCliResult(
        ok=proc.returncode == 0 and parsed is not None,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        json_value=parsed,
    )


def fetch_pricing_markdown() -> str:
    candidates = [
        "https://r.jina.ai/http://www.together.ai/pricing",
        TOGETHER_PRICING_URL,
    ]
    for url in candidates:
        request = Request(url, headers={"User-Agent": "odyn-together-normalizer/1.0"})
        try:
            with urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8", errors="replace")
            if "Supervised Fine-Tuning" in text or "Minimum charge" in text:
                return text
            if url == TOGETHER_PRICING_URL:
                return text
        except Exception:
            continue
    return ""


def list_all_fine_tuning_jobs(env: dict[str, str] | None = None, max_pages: int = 50) -> tuple[list[dict[str, Any]], list[TogetherCliResult]]:
    pages: list[TogetherCliResult] = []
    all_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    after: str | None = None

    for _ in range(max_pages):
        args = ["fine-tuning", "list"]
        if after:
            args.extend(["--after", after])
        result = run_together_cli_json(args, env=env)
        pages.append(result)
        if not result.ok:
            break
        payload = result.json_value
        if not isinstance(payload, list) or not payload:
            break

        new_added = 0
        for job in payload:
            job_id = str(job.get("id") or "")
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(job)
                new_added += 1
        last_id = str(payload[-1].get("id") or "")
        if new_added == 0 or not last_id or last_id == after:
            break
        after = last_id

    return all_jobs, pages


def select_benchmark_jobs(jobs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for job in jobs:
        model = str(job.get("model", "")).lower()
        if "qwen3.5-" in model or "gpt-oss-20b" in model:
            out.append(job)
    return out


def normalize_job_record(job: dict[str, Any]) -> dict[str, Any]:
    created = parse_iso8601(job.get("created_at"))
    started = parse_iso8601(job.get("started_at"))
    finished = parse_iso8601(job.get("updated_at"))
    training_type = job.get("training_type") or {}
    record = {
        "job_id": job.get("id"),
        "model": job.get("model"),
        "status": job.get("status"),
        "training_method": (job.get("training_method") or {}).get("method"),
        "lora_rank": training_type.get("lora_r"),
        "lora_target_modules": training_type.get("lora_trainable_modules"),
        "batch_size": job.get("batch_size"),
        "steps": job.get("max_steps"),
        "tokens": job.get("token_count"),
        "billed_usd": parse_together_price_units(job.get("total_price")),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("updated_at"),
        "queue_min": round3(minutes_between(created, started)),
        "training_min": round3(minutes_between(started, finished)),
        "wall_min": round3(minutes_between(created, finished)),
    }
    record["expected_steps_at_4096"] = expected_steps(record["tokens"], record["batch_size"], 4096)
    if record["steps"] in (None, -1):
        record["steps_far_from_expected"] = "UNAVAILABLE"
    elif record["expected_steps_at_4096"] is None:
        record["steps_far_from_expected"] = "UNAVAILABLE"
    else:
        observed = int(record["steps"])
        expected = int(record["expected_steps_at_4096"])
        record["steps_far_from_expected"] = abs(observed - expected) > max(2, int(expected * 0.2))
    if record["tokens"] and record["billed_usd"] is not None:
        record["together_effective_usd_per_million"] = round3(record["billed_usd"] / (record["tokens"] / 1_000_000.0))
    else:
        record["together_effective_usd_per_million"] = None
    return record


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers: list[str] = []
    for row in rows:
        for k in row.keys():
            if k not in headers:
                headers.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            normalized = {
                k: (round3(v) if isinstance(v, float) else v)
                for k, v in row.items()
            }
            writer.writerow(normalized)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def validate_regression_counts(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_model_tokens: dict[str, set[int]] = {}
    for row in rows:
        model = str(row.get("model", "")).lower()
        tokens = row.get("tokens")
        if isinstance(tokens, int):
            by_model_tokens.setdefault(model, set()).add(tokens)

    qwen_tokens = set()
    for model, values in by_model_tokens.items():
        if "qwen/qwen3.5-" in model:
            qwen_tokens |= values
    for label in ["qwen_1k", "qwen_5k", "qwen_10k"]:
        expected = EXPECTED_TOKEN_COUNTS[label]
        if expected not in qwen_tokens:
            errors.append(f"Missing expected Qwen token_count={expected}")

    gpt_tokens = set()
    for model, values in by_model_tokens.items():
        if "gpt-oss-20b" in model:
            gpt_tokens |= values
    if EXPECTED_TOKEN_COUNTS["gpt_oss_5k"] not in gpt_tokens:
        errors.append(f"Missing expected gpt-oss-20b token_count={EXPECTED_TOKEN_COUNTS['gpt_oss_5k']}")
    return errors


def now_utc_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

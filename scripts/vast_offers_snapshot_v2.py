#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class VastSnapshotConfig:
    query: str
    limit: int
    storage_gib: float
    order: str
    price_type: str
    output_dir: Path
    vastai_binary: str
    gcp_project: Optional[str]
    gcp_secret_name: Optional[str]


def _run(cmd: List[str], input_text: str | None = None) -> str:
    proc = subprocess.run(cmd, input=input_text, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def _now_utc_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _as_int(value: Any) -> Optional[int]:
    f = _as_float(value)
    if f is None:
        return None
    try:
        return int(f)
    except Exception:
        return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "t", "1", "yes", "y"}:
            return True
        if s in {"false", "f", "0", "no", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _round(value: Optional[float], digits: int) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _load_api_key(cfg: VastSnapshotConfig) -> None:
    if (os.getenv("VASTAI_API_KEY") or "").strip() or (os.getenv("VAST_API_KEY") or "").strip():
        return

    secret_name = (cfg.gcp_secret_name or os.getenv("VAST_GCP_SECRET_NAME") or "VASTAI_API_KEY").strip()
    project = (cfg.gcp_project or os.getenv("VAST_GCP_PROJECT") or "project-dalia").strip()
    if not project:
        raise RuntimeError(
            "Vast API key is not set and VAST_GCP_PROJECT is missing. "
            "Set VASTAI_API_KEY/VAST_API_KEY or provide --gcp-project."
        )

    key = _run([
        "gcloud",
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret",
        secret_name,
        "--project",
        project,
    ]).strip()
    if not key:
        raise RuntimeError(f"Secret {secret_name} in project {project} returned empty value")

    os.environ["VASTAI_API_KEY"] = key
    os.environ["VAST_API_KEY"] = key


def _search_offers(cfg: VastSnapshotConfig) -> List[Dict[str, Any]]:
    cmd: List[str] = [
        cfg.vastai_binary,
        "search",
        "offers",
        "--raw",
        cfg.query,
        "--limit",
        str(cfg.limit),
        "--storage",
        str(cfg.storage_gib),
        "--order",
        cfg.order,
    ]

    if cfg.price_type == "bid":
        cmd.append("--bid")
    elif cfg.price_type == "reserved":
        cmd.append("--reserved")
    else:
        cmd.append("--on-demand")

    stdout = _run(cmd)
    parsed = json.loads(stdout)
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]

    if isinstance(parsed, dict):
        # Defensive handling if CLI response shape changes.
        if isinstance(parsed.get("offers"), list):
            return [x for x in parsed["offers"] if isinstance(x, dict)]
        if isinstance(parsed.get("results"), list):
            return [x for x in parsed["results"] if isinstance(x, dict)]

    raise RuntimeError("Unexpected Vast CLI JSON response shape")


def _normalized_offer(row: Dict[str, Any], snapshot_ts: str, query: str, price_type: str) -> Dict[str, Any]:
    gpu_ram = _as_float(row.get("gpu_ram"))
    num_gpus = _as_int(row.get("num_gpus"))
    gpu_total_ram = _as_float(row.get("gpu_total_ram"))
    if gpu_total_ram is None and gpu_ram is not None and num_gpus is not None:
        gpu_total_ram = gpu_ram * num_gpus

    return {
        "snapshot_ts": snapshot_ts,
        "query": query,
        "pricing_mode": price_type,
        "offer_id": _as_int(row.get("id")),
        "machine_id": _as_int(row.get("machine_id")),
        "gpu_vendor": _as_text(row.get("gpu_arch")),
        "gpu_model": _as_text(row.get("gpu_name") or row.get("gpu")),
        "gpu_count": num_gpus,
        "cuda_version": _round(_as_float(row.get("cuda_vers") or row.get("cuda_version")), 2),
        "driver_version": _as_text(row.get("driver_version")),
        "gpu_memory_gb": _round(gpu_ram, 2),
        "total_gpu_memory_gb": _round(gpu_total_ram, 2),
        "total_flops": _round(_as_float(row.get("total_flops")), 3),
        "hourly_price_usd": _round(_as_float(row.get("dph")), 6),
        "flops_per_dollar": _round(_as_float(row.get("flops_usd")), 6),
        "dlperf": _round(_as_float(row.get("dlperf")), 4),
        "dlperf_per_dollar": _round(_as_float(row.get("dlperf_usd")), 6),
        "reliability_score": _round(_as_float(row.get("reliability")), 6),
        "gpu_max_power_watts": _round(_as_float(row.get("gpu_max_power")), 2),
        "gpu_max_temp_c": _round(_as_float(row.get("gpu_max_temp")), 2),
        "network_download_mbps": _round(_as_float(row.get("inet_down")), 2),
        "network_upload_mbps": _round(_as_float(row.get("inet_up")), 2),
        "cpu_architecture": _as_text(row.get("cpu_arch")),
        "cpu_cores": _as_int(row.get("cpu_cores")),
        "cpu_ram_gb": _round(_as_float(row.get("cpu_ram")), 2),
        "geolocation": _as_text(row.get("geolocation")),
        "verified": _as_bool(row.get("verified")),
        "rentable": _as_bool(row.get("rentable")),
        "external": _as_bool(row.get("external")),
        "datacenter": _as_bool(row.get("datacenter")),
        "min_bid_usd": _round(_as_float(row.get("min_bid")), 6),
    }


def _row_quality_score(row: Dict[str, Any]) -> Tuple[int, float, float]:
    non_nulls = sum(1 for v in row.values() if v is not None)
    reliability = row.get("reliability_score") or 0.0
    flops = row.get("total_flops") or 0.0
    return non_nulls, float(reliability), float(flops)


def _dedup(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        offer_id = row.get("offer_id")
        if offer_id is not None:
            key = f"offer:{offer_id}"
        else:
            key = "|".join(
                [
                    str(row.get("machine_id") or ""),
                    str(row.get("gpu_model") or ""),
                    str(row.get("gpu_count") or ""),
                    str(row.get("hourly_price_usd") or ""),
                    str(row.get("geolocation") or ""),
                ]
            )

        prev = best.get(key)
        if prev is None or _row_quality_score(row) > _row_quality_score(prev):
            best[key] = row
    return list(best.values())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
            c += 1
    return c


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture and normalize Vast AI offer telemetry with stable deduped formatting.")
    p.add_argument(
        "--query",
        default="external=false rentable=true verified=true",
        help="Vast search query. Default matches dependable public offers.",
    )
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--storage-gib", type=float, default=5.0)
    p.add_argument("--order", default="score-")
    p.add_argument("--price-type", choices=["on-demand", "bid", "reserved"], default="on-demand")
    p.add_argument("--output-dir", default="outputs/vast")
    p.add_argument("--vastai-binary", default=os.getenv("VASTAI_BIN") or "vastai")
    p.add_argument("--gcp-project", default=os.getenv("VAST_GCP_PROJECT") or "project-dalia")
    p.add_argument("--gcp-secret-name", default=os.getenv("VAST_GCP_SECRET_NAME") or "VASTAI_API_KEY")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = VastSnapshotConfig(
        query=args.query,
        limit=args.limit,
        storage_gib=args.storage_gib,
        order=args.order,
        price_type=args.price_type,
        output_dir=Path(args.output_dir),
        vastai_binary=args.vastai_binary,
        gcp_project=args.gcp_project,
        gcp_secret_name=args.gcp_secret_name,
    )

    _load_api_key(cfg)

    ts = _now_utc_compact()
    raw_rows = _search_offers(cfg)
    normalized = [_normalized_offer(row, snapshot_ts=ts, query=cfg.query, price_type=cfg.price_type) for row in raw_rows]
    deduped = _dedup(normalized)

    out_raw = cfg.output_dir / f"vast_offers_raw_{ts}.json"
    out_norm_json = cfg.output_dir / f"vast_offers_normalized_{ts}.json"
    out_norm_jsonl = cfg.output_dir / f"vast_offers_normalized_{ts}.jsonl"

    _write_json(out_raw, raw_rows)
    _write_json(out_norm_json, deduped)
    written = _write_jsonl(out_norm_jsonl, deduped)

    print(
        json.dumps(
            {
                "status": "ok",
                "snapshot_ts": ts,
                "query": cfg.query,
                "price_type": cfg.price_type,
                "raw_offers": len(raw_rows),
                "deduped_offers": len(deduped),
                "written_jsonl_rows": written,
                "outputs": {
                    "raw_json": str(out_raw),
                    "normalized_json": str(out_norm_json),
                    "normalized_jsonl": str(out_norm_jsonl),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

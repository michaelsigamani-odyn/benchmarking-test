from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class PlanConfig:
    source_json: str
    output_root: str
    sample_size: int
    dau_count: int
    seed: int
    fail_every: int


@dataclass(frozen=True)
class DauJob:
    dau_id: int
    seed: int
    dataset_path: str
    should_fail: bool
    expected_result: str


@dataclass(frozen=True)
class PlanPayload:
    source_json: str
    sample_size: int
    dau_count: int
    seed: int
    fail_every: int
    jobs: List[DauJob]


def parse_args() -> PlanConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", default="data/hf_alpaca_cleaned/alpaca_data_cleaned.json")
    parser.add_argument("--output-root", default="data/dau_16k_50")
    parser.add_argument("--sample-size", type=int, default=16000)
    parser.add_argument("--dau-count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--fail-every", type=int, default=10)
    args = parser.parse_args()
    return PlanConfig(args.source_json, args.output_root, args.sample_size, args.dau_count, args.seed, args.fail_every)


def read_rows(path: str) -> List[Dict[str, Any]]:
    rows = json.loads(Path(path).read_text())
    assert isinstance(rows, list) and rows, f"invalid source dataset: {path}"
    return [dict(row) for row in rows]


def shuffled_sample(rows: List[Dict[str, Any]], count: int, seed: int) -> List[Dict[str, Any]]:
    assert len(rows) >= count, f"dataset has {len(rows)} rows, need {count}"
    rng = random.Random(seed)
    selected = rng.sample(rows, count)
    rng.shuffle(selected)
    return selected


def chunk_size(total_rows: int, dau_count: int) -> int:
    return math.ceil(total_rows / dau_count)


def is_failure_job(dau_id: int, fail_every: int) -> bool:
    return fail_every > 0 and dau_id % fail_every == 0


def build_job(root: Path, dau_id: int, seed: int, fail_every: int) -> DauJob:
    failed = is_failure_job(dau_id, fail_every)
    path = str(root / "shards" / f"dau_{dau_id:02d}.jsonl")
    return DauJob(dau_id, seed + dau_id, path, failed, "injected_failure" if failed else "success")


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
    path.write_text(body + "\n")


def build_jobs(root: Path, count: int, fail_every: int, seed: int) -> List[DauJob]:
    return [build_job(root, idx + 1, seed, fail_every) for idx in range(count)]


def shard_rows(rows: List[Dict[str, Any]], count: int) -> List[List[Dict[str, Any]]]:
    size = chunk_size(len(rows), count)
    return [rows[idx * size : (idx + 1) * size] for idx in range(count)]


def write_shards(jobs: List[DauJob], shards: List[List[Dict[str, Any]]]) -> None:
    for job, shard in zip(jobs, shards):
        write_jsonl(Path(job.dataset_path), shard)


def to_payload(cfg: PlanConfig, jobs: List[DauJob]) -> PlanPayload:
    return PlanPayload(cfg.source_json, cfg.sample_size, cfg.dau_count, cfg.seed, cfg.fail_every, jobs)


def write_plan(path: Path, jobs: List[DauJob], cfg: PlanConfig) -> None:
    payload = asdict(to_payload(cfg, jobs))
    path.write_text(json.dumps(payload, indent=2))


def summary(root: Path, rows: List[Dict[str, Any]], jobs: List[DauJob], count: int) -> Dict[str, Any]:
    return {"output_root": str(root), "rows": len(rows), "jobs": len(jobs), "chunk_size": chunk_size(len(rows), count)}


def main() -> None:
    cfg = parse_args()
    rows = shuffled_sample(read_rows(cfg.source_json), cfg.sample_size, cfg.seed)
    root = Path(cfg.output_root)
    jobs = build_jobs(root, cfg.dau_count, cfg.fail_every, cfg.seed)
    write_shards(jobs, shard_rows(rows, cfg.dau_count))
    write_plan(root / "plan.json", jobs, cfg)
    print(json.dumps(summary(root, rows, jobs, cfg.dau_count), indent=2))


if __name__ == "__main__":
    main()

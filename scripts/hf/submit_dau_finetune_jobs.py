from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class SubmitConfig:
    plan_path: str
    image: str
    namespace: str
    dry_run: bool
    model_id: str
    mount_root: str
    flavor: str
    timeout: str
    volume: str


@dataclass(frozen=True)
class SubmitResult:
    dau_id: int
    expected_result: str
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PlanJob:
    dau_id: int
    seed: int
    dataset_path: str
    should_fail: bool
    expected_result: str


@dataclass(frozen=True)
class PlanPayload:
    jobs: List[PlanJob]


def parse_args() -> SubmitConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-path", default="data/dau_16k_50/plan.json")
    parser.add_argument("--image", default="python:3.12")
    parser.add_argument("--namespace", default="")
    parser.add_argument("--model-id", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument("--mount-root", default="/workspace")
    parser.add_argument("--flavor", default="cpu-basic")
    parser.add_argument("--timeout", default="45m")
    parser.add_argument("--volume", default="hf://buckets/michael-sigamani-odyn/dau-failure-policy:/workspace:ro")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()
    return SubmitConfig(args.plan_path, args.image, args.namespace, not args.submit, args.model_id, args.mount_root, args.flavor, args.timeout, args.volume)


def _to_job(payload: Dict[str, Any]) -> PlanJob:
    return PlanJob(int(payload["dau_id"]), int(payload["seed"]), str(payload["dataset_path"]), bool(payload["should_fail"]), str(payload["expected_result"]))


def read_plan(path: str) -> PlanPayload:
    payload = dict(json.loads(Path(path).read_text()))
    return PlanPayload([_to_job(job) for job in list(payload.get("jobs", []))])


def _missing_dataset_path(job: PlanJob, mount_root: str) -> str:
    return f"{mount_root}/data/dau_16k_50/shards/missing_{job.dau_id:02d}.jsonl"


def _mounted_dataset_path(job: PlanJob, mount_root: str) -> str:
    return f"{mount_root}/data/dau_16k_50/shards/{Path(job.dataset_path).name}"


def dataset_arg(job: PlanJob, mount_root: str) -> str:
    return _missing_dataset_path(job, mount_root) if job.should_fail else _mounted_dataset_path(job, mount_root)


def _mount(cfg: SubmitConfig) -> str:
    return cfg.volume


def _labels(job: PlanJob) -> List[str]:
    return ["--label", "workload=dau-finetune", "--label", f"dau_id={job.dau_id}", "--label", f"expected={job.expected_result}"]


def _scope_args(cfg: SubmitConfig) -> List[str]:
    return (["--namespace", cfg.namespace] if cfg.namespace else []) + (["--dry-run"] if cfg.dry_run else ["--detach"])


def _entrypoint_args(cfg: SubmitConfig, job: PlanJob) -> List[str]:
    return ["python", f"{cfg.mount_root}/scripts/finetuning/hf_dau_entrypoint.py", "--model-id", cfg.model_id, "--dataset-path", dataset_arg(job, cfg.mount_root), "--output-dir", f"/tmp/out_dau_{job.dau_id:02d}", "--seed", str(job.seed), "--stop-step", "3", "--max-steps", "5", "--per-device-batch-size", "1"]


def hf_command(cfg: SubmitConfig, job: PlanJob) -> List[str]:
    opts = ["hf", "jobs", "run", "--flavor", cfg.flavor, "--timeout", cfg.timeout, "--volume", _mount(cfg), "--name", f"dau-{job.dau_id:02d}-finetune"]
    return opts + _labels(job) + _scope_args(cfg) + [cfg.image] + _entrypoint_args(cfg, job)


def run_job(cfg: SubmitConfig, job: PlanJob) -> SubmitResult:
    proc = subprocess.run(hf_command(cfg, job), text=True, capture_output=True)
    return SubmitResult(job.dau_id, job.expected_result, proc.returncode, proc.stdout, proc.stderr)


def write_report(path: Path, rows: List[SubmitResult], cfg: SubmitConfig) -> None:
    payload = {"dry_run": cfg.dry_run, "submitted": len(rows), "failures": sum(1 for row in rows if row.returncode != 0), "results": [asdict(row) for row in rows]}
    path.write_text(json.dumps(payload, indent=2))


def run_jobs(cfg: SubmitConfig, plan: PlanPayload) -> List[SubmitResult]:
    return [run_job(cfg, job) for job in plan.jobs]


def main() -> None:
    cfg = parse_args()
    plan = read_plan(cfg.plan_path)
    rows = run_jobs(cfg, plan)
    report = Path(cfg.plan_path).with_name("submission_report.json")
    write_report(report, rows, cfg)
    print(json.dumps({"dry_run": cfg.dry_run, "jobs": len(rows), "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()

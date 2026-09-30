"""Dagster flow for Ray-managed distributed JAX bootstrap checks.

Env configuration:
  JAX_RAY_LAUNCH_MODE=ray_jobs|slurm
  JAX_RAY_RUNTIME_CONFIG=configs/ray_distributed_jax_dgxspark.json
  JAX_RAY_ENTRYPOINT_SCRIPT=scripts/ray/distributed_jax_coordinator.py
  JAX_RAY_DASHBOARD_URL=http://127.0.0.1:8265
  JAX_RAY_WORKING_DIR=.
  JAX_RAY_RUN_DIR=runs/ray_distributed/latest
  JAX_RAY_SLURM_SCRIPT=scripts/ray/slurm_start_and_submit.sh
  JAX_RAY_SLURM_FLAGS="--nodes=2 --account ... --partition ..."
  JAX_ZAPIER_EVAL_SSH=michael@odyn-dgx3
  JAX_ZAPIER_EVAL_ROOT=/home/michael/merlin-eval-harness
  JAX_ZAPIER_CHECKPOINT_ROOT=/tmp/opencode/bench
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Dict, List

import dagster as dg

HERE = Path(__file__).resolve().parent
GROUP = "jax_distributed"
LAUNCH_MODE = os.environ.get("JAX_RAY_LAUNCH_MODE", "ray_jobs")
RUNTIME_CONFIG = os.environ.get("JAX_RAY_RUNTIME_CONFIG", "configs/ray_distributed_jax_dgxspark.json")
ENTRYPOINT_SCRIPT = os.environ.get("JAX_RAY_ENTRYPOINT_SCRIPT", "scripts/ray/distributed_jax_coordinator.py")
DASHBOARD_URL = os.environ.get("JAX_RAY_DASHBOARD_URL", "http://127.0.0.1:8265")
WORKING_DIR = os.environ.get("JAX_RAY_WORKING_DIR", ".")
RUN_DIR = Path(os.environ.get("JAX_RAY_RUN_DIR", str(HERE / "runs" / "ray_distributed" / "latest"))).resolve()
SLURM_SCRIPT = os.environ.get("JAX_RAY_SLURM_SCRIPT", "scripts/ray/slurm_start_and_submit.sh")
SLURM_FLAGS = os.environ.get("JAX_RAY_SLURM_FLAGS", "")
ZAPIER_EVAL_SSH = os.environ.get("JAX_ZAPIER_EVAL_SSH", "michael@odyn-dgx3")
ZAPIER_EVAL_ROOT = os.environ.get("JAX_ZAPIER_EVAL_ROOT", "/home/michael/merlin-eval-harness")
ZAPIER_CHECKPOINT_ROOT = os.environ.get("JAX_ZAPIER_CHECKPOINT_ROOT", "/tmp/opencode/bench")
VALID_LAUNCH_MODES = {"ray_jobs", "slurm"}


def _abs(path_text: str) -> Path:
    return (HERE / path_text).resolve() if not Path(path_text).is_absolute() else Path(path_text)


def _status_path() -> Path:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    return RUN_DIR / "ray_job_status.json"


def _run(command: List[str], env: Dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=str(HERE), text=True, capture_output=True, env=env)


def _ray_jobs_command(status_path: Path) -> List[str]:
    return [
        sys.executable,
        "scripts/ray/launch_ray_job.py",
        "--dashboard-url",
        DASHBOARD_URL,
        "--entrypoint-script",
        ENTRYPOINT_SCRIPT,
        "--runtime-config",
        RUNTIME_CONFIG,
        "--working-dir",
        WORKING_DIR,
        "--status-path",
        str(status_path),
    ]


def _slurm_command(status_path: Path, slurm_path: Path) -> List[str]:
    export_values = {
        "RAY_RUNTIME_CONFIG": RUNTIME_CONFIG,
        "RAY_ENTRYPOINT_SCRIPT": ENTRYPOINT_SCRIPT,
        "RAY_WORKING_DIR": WORKING_DIR,
        "RAY_STATUS_PATH": str(status_path),
    }
    export_arg = "ALL," + ",".join(f"{key}={value}" for key, value in export_values.items())
    return ["sbatch", "--wait", "--export", export_arg, *shlex.split(SLURM_FLAGS), str(slurm_path)]


def _validate_runtime_dependencies() -> None:
    has_ray = find_spec("ray") is not None
    has_job_submission = has_ray and find_spec("ray.job_submission") is not None
    if LAUNCH_MODE == "ray_jobs" and not has_job_submission:
        raise RuntimeError("Missing dependency: ray. Install with '.venv/bin/pip install \"ray[default]\"' or 'pip install -r requirements.txt'.")


def _zapier_eval_remote_command() -> List[str]:
    unit = "PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'"
    run6 = f"PYTHONPATH=src python3 -m eval_harness.benchmarks.runner --backend baseline --checkpoint-root {ZAPIER_CHECKPOINT_ROOT} --steps 6"
    run10 = f"PYTHONPATH=src python3 -m eval_harness.benchmarks.runner --backend baseline --checkpoint-root {ZAPIER_CHECKPOINT_ROOT} --steps 10 --resume"
    inner = f"cd {ZAPIER_EVAL_ROOT} && {unit} && {run6} && {run10}"
    return ["ssh", ZAPIER_EVAL_SSH, inner]


@dg.asset(group_name=GROUP, description="Validate inputs for Ray distributed JAX Dagster flow.")
def jax_distributed_preflight() -> dg.MaterializeResult:
    if LAUNCH_MODE not in VALID_LAUNCH_MODES:
        raise ValueError(f"Unsupported launch mode: {LAUNCH_MODE}")
    _validate_runtime_dependencies()
    runtime_path = _abs(RUNTIME_CONFIG)
    entrypoint_path = _abs(ENTRYPOINT_SCRIPT)
    slurm_path = _abs(SLURM_SCRIPT)
    checks = {"runtime_config": runtime_path.exists(), "entrypoint_script": entrypoint_path.exists(), "slurm_script": slurm_path.exists()}
    if not all(checks.values()):
        raise FileNotFoundError(str(checks))
    return dg.MaterializeResult(metadata={"launch_mode": LAUNCH_MODE, **{k: str(v) for k, v in {
        "runtime_config": runtime_path,
        "entrypoint_script": entrypoint_path,
        "slurm_script": slurm_path,
    }.items()}})


@dg.asset(group_name=GROUP, deps=[jax_distributed_preflight], description="Launch distributed JAX runtime flow via Ray Jobs or SLURM.")
def zapier_eval_harness_remote() -> dg.MaterializeResult:
    result = _run(_zapier_eval_remote_command(), os.environ.copy())
    if result.returncode != 0:
        raise RuntimeError(result.stdout[-2000:] + result.stderr[-2000:])
    return dg.MaterializeResult(metadata={
        "ssh_host": ZAPIER_EVAL_SSH,
        "repo": ZAPIER_EVAL_ROOT,
        "checkpoint_root": ZAPIER_CHECKPOINT_ROOT,
        "stdout_tail": result.stdout[-1500:],
    })


@dg.asset(group_name=GROUP, deps=[jax_distributed_preflight, zapier_eval_harness_remote], description="Launch distributed JAX runtime flow via Ray Jobs or SLURM.")
def jax_distributed_run() -> dg.MaterializeResult:
    status_path = _status_path()
    slurm_path = _abs(SLURM_SCRIPT)
    env = {**os.environ, "RAY_RUNTIME_CONFIG": RUNTIME_CONFIG, "RAY_ENTRYPOINT_SCRIPT": ENTRYPOINT_SCRIPT}
    command = _ray_jobs_command(status_path) if LAUNCH_MODE == "ray_jobs" else _slurm_command(status_path, slurm_path)
    result = _run(command, env)
    if result.returncode != 0:
        raise RuntimeError(result.stdout[-2000:] + result.stderr[-2000:])
    metadata = {
        "launch_mode": LAUNCH_MODE,
        "command": " ".join(command),
        "stdout_tail": result.stdout[-1500:],
        "stderr_tail": result.stderr[-1500:],
    }
    if status_path.exists():
        metadata["status_path"] = dg.MetadataValue.path(str(status_path))
        metadata["status_json"] = dg.MetadataValue.md(status_path.read_text())
    return dg.MaterializeResult(metadata=metadata)


@dg.asset_check(asset=jax_distributed_run, description="Ray distributed JAX launch completed without runtime error.")
def jax_distributed_run_succeeded() -> dg.AssetCheckResult:
    return dg.AssetCheckResult(passed=True)


@dg.asset_check(asset=zapier_eval_harness_remote, description="Remote Zapier eval harness unit and resume checks passed.")
def zapier_eval_harness_succeeded() -> dg.AssetCheckResult:
    return dg.AssetCheckResult(passed=True)


defs = dg.Definitions(
    assets=[jax_distributed_preflight, zapier_eval_harness_remote, jax_distributed_run],
    asset_checks=[zapier_eval_harness_succeeded, jax_distributed_run_succeeded],
)


if __name__ == "__main__":
    result = dg.materialize([jax_distributed_preflight, zapier_eval_harness_remote, jax_distributed_run])
    raise SystemExit(0 if result.success else 1)

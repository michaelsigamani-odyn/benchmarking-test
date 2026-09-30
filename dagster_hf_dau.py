from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dagster import In, Nothing, OpExecutionContext, job, op


@dataclass(frozen=True)
class HfDauConfig:
    namespace: str
    submit: bool


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _base_command(script: str) -> List[str]:
    return ["python3", str(_repo_root() / script)]


def _namespace() -> str:
    return os.getenv("HF_DAU_NAMESPACE", "michael-sigamani-odyn")


def _submit() -> bool:
    return os.getenv("HF_DAU_SUBMIT", "false").lower() == "true"


def _config() -> HfDauConfig:
    return HfDauConfig(_namespace(), _submit())


def _run(command: List[str]) -> None:
    subprocess.run(command, cwd=_repo_root(), check=True)


def _submit_command(cfg: HfDauConfig) -> List[str]:
    mode = ["--submit"] if cfg.submit else []
    return _base_command("scripts/hf/submit_dau_finetune_jobs.py") + mode + ["--namespace", cfg.namespace]


@op
def prepare_hf_dau_plan(context: OpExecutionContext) -> None:
    context.log.info("Generating DAU plan")
    _run(_base_command("scripts/hf/prepare_dau_finetune_plan.py"))


@op(ins={"start": In(Nothing)})
def submit_hf_dau_jobs(context: OpExecutionContext) -> None:
    cfg = _config()
    context.log.info(f"Submitting mode submit={cfg.submit} namespace={cfg.namespace}")
    _run(_submit_command(cfg))


@job
def hf_dau_finetune_job() -> None:
    submit_hf_dau_jobs(prepare_hf_dau_plan())

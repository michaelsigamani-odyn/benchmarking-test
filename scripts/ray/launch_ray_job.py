from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ray.job_submission import JobStatus, JobSubmissionClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:8265")
    parser.add_argument("--runtime-config", required=True)
    parser.add_argument("--entrypoint-script", default="scripts/ray/resilient_coordinator.py")
    parser.add_argument("--working-dir", default=".")
    parser.add_argument("--status-path", default="")
    return parser.parse_args()


def _print_incremental_logs(client: JobSubmissionClient, job_id: str, prev_logs: str) -> str:
    logs = client.get_job_logs(job_id)
    print(logs[len(prev_logs) :], end="", flush=True)
    return logs


def main() -> None:
    args = _parse_args()
    client = JobSubmissionClient(args.dashboard_url)
    job_id = client.submit_job(
        entrypoint=f"{sys.executable} {args.entrypoint_script} --runtime-config {args.runtime_config}",
        runtime_env={"working_dir": args.working_dir},
    )
    print(f"job_id={job_id}", flush=True)
    prev_logs = ""
    while True:
        status = client.get_job_status(job_id)
        if status == JobStatus.RUNNING:
            prev_logs = _print_incremental_logs(client, job_id, prev_logs)
        if status in {JobStatus.SUCCEEDED, JobStatus.STOPPED, JobStatus.FAILED}:
            print(f"\nfinal_status={status}", flush=True)
            if status in {JobStatus.STOPPED, JobStatus.FAILED}:
                print(client.get_job_logs(job_id), flush=True)
            break
        time.sleep(5)
    payload = {"job_id": job_id, "final_status": str(status), "dashboard_url": args.dashboard_url}
    if args.status_path:
        Path(args.status_path).write_text(json.dumps(payload, indent=2))
    if status in {JobStatus.STOPPED, JobStatus.FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

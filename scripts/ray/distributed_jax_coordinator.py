from __future__ import annotations

import argparse
import json
import os
import random
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import ray


@dataclass
class DistributedConfig:
    workers: int
    cpus_per_worker: int
    gpus_per_worker: int
    worker_resource_key: str
    worker_resource_value: int
    timeout_s: int


def _read_config(path: str) -> DistributedConfig:
    payload = json.loads(Path(path).read_text())
    return DistributedConfig(
        workers=int(payload.get("workers", int(os.environ.get("NGPUS", "1")))),
        cpus_per_worker=int(payload.get("cpus_per_worker", 16)),
        gpus_per_worker=int(payload.get("gpus_per_worker", 1)),
        worker_resource_key=payload.get("worker_resource_key", "worker_units"),
        worker_resource_value=int(payload.get("worker_resource_value", 1)),
        timeout_s=int(payload.get("timeout_s", 1800)),
    )


def _coordinator_addr() -> str:
    host = socket.gethostbyname(socket.gethostname())
    port = random.randint(62000, 65535)
    return f"{host}:{port}"


@ray.remote
class DistributedJaxWorker:
    def run(self, process_id: int, coordinator_addr: str, num_processes: int) -> Dict[str, Any]:
        import jax
        import jax.numpy as jnp
        from jax.experimental import multihost_utils

        jax.distributed.initialize(
            coordinator_address=coordinator_addr,
            num_processes=num_processes,
            process_id=process_id,
            local_device_ids=0,
        )
        gathered = np.asarray(multihost_utils.process_allgather(jnp.array([jax.process_index()], dtype=jnp.int32))).tolist()
        devices = [str(device) for device in jax.devices()]
        return {
            "process_id": process_id,
            "process_index": int(jax.process_index()),
            "process_count": int(jax.process_count()),
            "local_device_count": int(jax.local_device_count()),
            "global_device_count": int(jax.device_count()),
            "devices": devices,
            "allgather_process_indices": gathered,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-config", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = _read_config(args.runtime_config)
    ray.init(address="auto")
    options = {"num_gpus": cfg.gpus_per_worker, "num_cpus": cfg.cpus_per_worker}
    if cfg.worker_resource_key:
        options["resources"] = {cfg.worker_resource_key: cfg.worker_resource_value}
    workers: List[ray.actor.ActorHandle] = [DistributedJaxWorker.options(**options).remote() for _ in range(cfg.workers)]
    coordinator_addr = _coordinator_addr()
    refs = [worker.run.remote(i, coordinator_addr, cfg.workers) for i, worker in enumerate(workers)]
    outputs = ray.get(refs, timeout=cfg.timeout_s)
    print(json.dumps({"status": "ok", "workers": outputs}, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import ray
import redis


@dataclass
class RuntimeConfig:
    command: str
    cwd: str
    env: Dict[str, str]
    workers: int
    cpus_per_worker: int
    gpus_per_worker: int
    worker_resource_key: str
    worker_resource_value: int
    heartbeat_timeout_s: int
    monitor_interval_s: int
    max_restarts: int
    jax_distributed: bool


def _read_runtime_config(path: str) -> RuntimeConfig:
    payload = json.loads(Path(path).read_text())
    return RuntimeConfig(
        command=payload["command"],
        cwd=payload.get("cwd", "."),
        env=payload.get("env", {}),
        workers=int(payload.get("workers", int(os.environ.get("NGPUS", "1")))),
        cpus_per_worker=int(payload.get("cpus_per_worker", 16)),
        gpus_per_worker=int(payload.get("gpus_per_worker", 1)),
        worker_resource_key=payload.get("worker_resource_key", "worker_units"),
        worker_resource_value=int(payload.get("worker_resource_value", 1)),
        heartbeat_timeout_s=int(payload.get("heartbeat_timeout_s", 300)),
        monitor_interval_s=int(payload.get("monitor_interval_s", 15)),
        max_restarts=int(payload.get("max_restarts", 3)),
        jax_distributed=bool(payload.get("jax_distributed", False)),
    )


def _redis_client() -> redis.Redis:
    host, port = os.environ["REDIS_ADDR"].split(":", maxsplit=1)
    return redis.Redis(host=host, port=int(port), decode_responses=True)


def _coordinator_addr() -> str:
    host = socket.gethostbyname(socket.gethostname())
    port = random.randint(62000, 65535)
    return f"{host}:{port}"


def _redis_set(redis_client: redis.Redis, key: str, value: str) -> None:
    redis_client.set(key, value)


@ray.remote
class ResilientWorker:
    def __init__(self) -> None:
        self.redis = _redis_client()
        self.worker_id = -1

    def initialize(self, worker_id: int, coordinator_addr: str, num_workers: int, jax_distributed: bool) -> None:
        self.worker_id = worker_id
        if jax_distributed:
            import jax

            jax.distributed.initialize(
                coordinator_address=coordinator_addr,
                num_processes=num_workers,
                process_id=worker_id,
                local_device_ids=0,
            )

    def run(self, command: str, cwd: str, extra_env: Dict[str, str], monitor_interval_s: int) -> Dict[str, Any]:
        log_path = Path(cwd) / f"worker_{self.worker_id}.log"
        env = {**os.environ, **extra_env, "RAY_WORKER_ID": str(self.worker_id)}
        with log_path.open("w") as log_file:
            proc = subprocess.Popen(command, cwd=cwd, env=env, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
            while proc.poll() is None:
                _redis_set(self.redis, f"hb:{self.worker_id}", str(time.time()))
                time.sleep(monitor_interval_s)
            _redis_set(self.redis, f"hb:{self.worker_id}", str(time.time()))
        if proc.returncode != 0:
            tail = log_path.read_text(errors="ignore")[-1500:]
            raise RuntimeError(f"worker {self.worker_id} failed rc={proc.returncode}\n{tail}")
        return {"worker_id": self.worker_id, "log": str(log_path), "returncode": proc.returncode}


class RayClusterCoordinator:
    def __init__(self, cfg: RuntimeConfig) -> None:
        self.cfg = cfg
        self.redis = _redis_client()
        self.workers: List[ray.actor.ActorHandle] = []
        self._spawn_workers()

    def _spawn_workers(self) -> None:
        options = {"num_gpus": self.cfg.gpus_per_worker, "num_cpus": self.cfg.cpus_per_worker}
        if self.cfg.worker_resource_key:
            options["resources"] = {self.cfg.worker_resource_key: self.cfg.worker_resource_value}
        self.workers = [ResilientWorker.options(**options).remote() for _ in range(self.cfg.workers)]

    def initialize_workers(self) -> None:
        addr = _coordinator_addr()
        jobs = [w.initialize.remote(i, addr, self.cfg.workers, self.cfg.jax_distributed) for i, w in enumerate(self.workers)]
        ray.get(jobs)

    async def _run_workers_async(self) -> List[Dict[str, Any]]:
        refs = [w.run.remote(self.cfg.command, self.cfg.cwd, self.cfg.env, self.cfg.monitor_interval_s) for w in self.workers]
        pending, outputs = refs, []
        while pending:
            done, pending = ray.wait(pending, num_returns=1, timeout=self.cfg.monitor_interval_s)
            if not done:
                await asyncio.sleep(0)
                continue
            outputs.extend(ray.get(done))
        return outputs

    async def _detect_worker_hang_async(self) -> None:
        while True:
            await asyncio.sleep(self.cfg.monitor_interval_s)
            now = time.time()
            for worker_id in range(self.cfg.workers):
                stamp = self.redis.get(f"hb:{worker_id}")
                if stamp and now - float(stamp) > self.cfg.heartbeat_timeout_s:
                    raise RuntimeError(f"worker {worker_id} heartbeat timeout")

    def _kill_and_recreate(self) -> None:
        for worker in self.workers:
            ray.kill(worker, no_restart=True)
        self._spawn_workers()
        self.initialize_workers()

    async def run(self) -> List[Dict[str, Any]]:
        restarts = 0
        while True:
            tasks = [asyncio.create_task(self._run_workers_async()), asyncio.create_task(self._detect_worker_hang_async())]
            try:
                results = await asyncio.gather(*tasks)
                return results[0]
            except Exception:
                for task in tasks:
                    task.cancel()
                restarts += 1
                if restarts > self.cfg.max_restarts:
                    raise
                self.cfg.env["RAY_RESTORE"] = "1"
                self._kill_and_recreate()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-config", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = _read_runtime_config(args.runtime_config)
    ray.init(address="auto")
    coordinator = RayClusterCoordinator(cfg)
    coordinator.initialize_workers()
    result = asyncio.run(coordinator.run())
    print(json.dumps({"status": "ok", "workers": result}, indent=2))


if __name__ == "__main__":
    main()

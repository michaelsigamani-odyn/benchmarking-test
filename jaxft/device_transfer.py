from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional, Tuple
from uuid import uuid4

import jax
import jax.numpy as jnp
import numpy as np

BYTES_PER_MEGABYTE = 1024 * 1024
BENCHMARK_MB = 8
BENCHMARK_REPEATS = 5


class MooncakeBenchmarkUnavailable(RuntimeError):
    pass


def tree_to_device(tree: Any) -> Any:
    return jax.tree.map(jax.device_put, tree)


def arrays_to_device(tokens: Any, mask: Any) -> Tuple[Any, Any]:
    return jax.device_put(tokens), jax.device_put(mask)


def tree_to_host(tree: Any) -> Any:
    return jax.tree.map(jax.device_get, tree)


def scalar_to_host(value: Any) -> float:
    return float(jax.device_get(value))


def sample_transfer_payload() -> Tuple[np.ndarray, np.ndarray]:
    tokens = np.arange(12, dtype=np.int32).reshape(3, 4)
    mask = (tokens % 2) == 0
    return tokens, mask


def _transfer_mbps(total_bytes: int, elapsed_seconds: float) -> float:
    return (total_bytes / BYTES_PER_MEGABYTE) / max(elapsed_seconds, 1e-9)


def _payload_bytes(megabytes: int) -> bytes:
    return b"x" * (megabytes * BYTES_PER_MEGABYTE)


def _python_executable() -> str:
    return "python3"


def _agent_script() -> Path:
    return Path(__file__).resolve().parents[1] / "mooncake_tcp_agent.py"


def _check_mooncake_runtime() -> None:
    try:
        from mooncake.engine import TransferEngine  # type: ignore # noqa: F401
    except Exception as exc:
        raise MooncakeBenchmarkUnavailable("mooncake.engine is not installed") from exc
    if not _agent_script().exists():
        raise MooncakeBenchmarkUnavailable("mooncake_tcp_agent.py is not available")


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _receiver_command(control_port: int, destination: Path, tmp_dir: Path, receiver_port: int, sender_port: int, session: str) -> list[str]:
    return [
        _python_executable(),
        str(_agent_script()),
        "--mode", "receiver",
        "--metadata-server", "P2PHANDSHAKE",
        "--protocol", "tcp",
        "--local-server-name", f"127.0.0.1:{receiver_port}",
        "--peer-server-name", f"127.0.0.1:{sender_port}",
        "--source-dir", "",
        "--destination-dir", str(destination),
        "--destination-tmp-dir", str(tmp_dir),
        "--control-host", "127.0.0.1",
        "--control-port", str(control_port),
        "--session-id", session,
    ]


def _sender_command(control_port: int, source: Path, destination: Path, tmp_dir: Path, receiver_port: int, sender_port: int, session: str) -> list[str]:
    return [
        _python_executable(),
        str(_agent_script()),
        "--mode", "sender",
        "--metadata-server", "P2PHANDSHAKE",
        "--protocol", "tcp",
        "--local-server-name", f"127.0.0.1:{sender_port}",
        "--peer-server-name", f"127.0.0.1:{receiver_port}",
        "--source-dir", str(source),
        "--destination-dir", str(destination),
        "--destination-tmp-dir", str(tmp_dir),
        "--control-host", "127.0.0.1",
        "--control-port", str(control_port),
        "--session-id", session,
    ]


def _wait_for_port(port: int, timeout_seconds: float) -> None:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise MooncakeBenchmarkUnavailable(f"receiver did not open control port {port}")


def _extract_sender_payload(stdout: str) -> dict:
    for line in reversed([row.strip() for row in stdout.splitlines() if row.strip()]):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "throughput_bytes_per_second" in payload:
            return payload
    raise MooncakeBenchmarkUnavailable("mooncake sender output did not include throughput payload")


def _terminate_process(process: Optional[subprocess.Popen[str]]) -> None:
    if not process or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()


def _time_mooncake_once(payload: bytes) -> float:
    _check_mooncake_runtime()
    with tempfile.TemporaryDirectory(prefix="mooncake-bench-") as root:
        source = Path(root) / "source"; destination = Path(root) / "destination"; tmp_dir = Path(root) / "tmp"
        source.mkdir(parents=True, exist_ok=True); destination.mkdir(parents=True, exist_ok=True); tmp_dir.mkdir(parents=True, exist_ok=True)
        (source / "payload.bin").write_bytes(payload)
        control_port = _free_port(); receiver_port = _free_port(); sender_port = _free_port(); session = f"bench-{uuid4().hex[:10]}"
        receiver = subprocess.Popen(_receiver_command(control_port, destination, tmp_dir, receiver_port, sender_port, session), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            _wait_for_port(control_port, 10.0)
            start = time.perf_counter()
            sender = subprocess.run(_sender_command(control_port, source, destination, tmp_dir, receiver_port, sender_port, session), capture_output=True, text=True, timeout=60)
            elapsed = time.perf_counter() - start
            if sender.returncode != 0:
                raise MooncakeBenchmarkUnavailable(f"mooncake sender failed rc={sender.returncode}: {sender.stderr[-500:]}")
            _extract_sender_payload(sender.stdout)
            return elapsed
        finally:
            _terminate_process(receiver)


def _time_mooncake_transfer(payload: bytes, repeats: int) -> float:
    return sum(_time_mooncake_once(payload) for _ in range(repeats))


def _time_device_put(payload: np.ndarray, repeats: int) -> float:
    start = time.perf_counter()
    for _ in range(repeats):
        jax.block_until_ready(jax.device_put(payload))
    return time.perf_counter() - start


def _time_device_get(payload: np.ndarray, repeats: int) -> float:
    device_payload = jax.device_put(payload)
    jax.block_until_ready(device_payload)
    start = time.perf_counter()
    for _ in range(repeats):
        np.asarray(jax.device_get(device_payload))
    return time.perf_counter() - start


def _recv_all(connection: socket.socket, total_bytes: int) -> None:
    remaining = total_bytes
    while remaining > 0:
        remaining -= len(connection.recv(min(remaining, 65536)))


def _tcp_sink(listener: socket.socket, total_bytes: int) -> None:
    with listener:
        connection, _ = listener.accept()
        with connection:
            _recv_all(connection, total_bytes)


def _time_tcp_transfer(payload: bytes, repeats: int) -> float:
    elapsed = 0.0
    for _ in range(repeats):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0)); listener.listen(1)
        worker = threading.Thread(target=_tcp_sink, args=(listener, len(payload)), daemon=True); worker.start()
        start = time.perf_counter()
        with socket.create_connection(("127.0.0.1", listener.getsockname()[1])) as client:
            client.sendall(payload)
        worker.join(); elapsed += time.perf_counter() - start
    return elapsed


def _select_floor_transfer(payload: bytes, repeats: int) -> tuple[str, float, Optional[str]]:
    try:
        return "mooncake", _time_mooncake_transfer(payload, repeats), None
    except Exception as exc:
        return "tcp", _time_tcp_transfer(payload, repeats), str(exc)


def transfer_speed_metrics() -> dict:
    payload = np.arange(BENCHMARK_MB * BYTES_PER_MEGABYTE, dtype=np.uint8)
    floor_payload = _payload_bytes(BENCHMARK_MB)
    put_elapsed = _time_device_put(payload, BENCHMARK_REPEATS)
    get_elapsed = _time_device_get(payload, BENCHMARK_REPEATS)
    floor_backend, floor_elapsed, fallback = _select_floor_transfer(floor_payload, BENCHMARK_REPEATS)
    total_bytes = payload.nbytes * BENCHMARK_REPEATS
    floor_mbps = _transfer_mbps(total_bytes, floor_elapsed)
    mooncake_mbps = floor_mbps if floor_backend == "mooncake" else None
    tcp_mbps = floor_mbps if floor_backend == "tcp" else None
    return {
        "jax_put_mbps": _transfer_mbps(total_bytes, put_elapsed),
        "jax_get_mbps": _transfer_mbps(total_bytes, get_elapsed),
        "transfer_floor_backend": floor_backend,
        "transfer_floor_mbps": floor_mbps,
        "mooncake_floor_mbps": mooncake_mbps,
        "tcp_floor_mbps": tcp_mbps,
        "transfer_floor_fallback_reason": fallback,
    }


def validate_transfer_roundtrip() -> dict:
    tokens, mask = sample_transfer_payload()
    device_tokens, device_mask = arrays_to_device(tokens, mask)
    host_tokens, host_mask = tree_to_host((device_tokens, device_mask))
    total = scalar_to_host(jnp.sum(device_tokens))
    speeds = transfer_speed_metrics()
    speed_values = [speeds["jax_put_mbps"], speeds["jax_get_mbps"], speeds["transfer_floor_mbps"]]
    speed_ok = all(np.isfinite(value) and value > 0 for value in speed_values)
    return {
        "roundtrip_ok": bool(np.array_equal(host_tokens, tokens) and np.array_equal(host_mask, mask)),
        "sum_ok": bool(total == float(tokens.sum())),
        "device_token_shape": list(device_tokens.shape),
        "host_token_shape": list(host_tokens.shape),
        "speed_ok": speed_ok,
        **speeds,
    }

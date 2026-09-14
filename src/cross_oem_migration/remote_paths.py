import shlex

from .execution.base import Executor


def resolve_remote_root(executor: Executor, host: str, remote_root: str, retries: int) -> str:
    resolved = expand_user_root(executor, host, remote_root, retries)
    normalized = normalize_path(resolved)
    executor.run(f"mkdir -p {shlex.quote(normalized)}", host=host, retries=retries)
    return normalized


def expand_user_root(executor: Executor, host: str, remote_root: str, retries: int) -> str:
    if remote_root == "~":
        return remote_home(executor, host, retries)
    if remote_root.startswith("~/"):
        return f"{remote_home(executor, host, retries)}/{remote_root[2:]}"
    return remote_root


def remote_home(executor: Executor, host: str, retries: int) -> str:
    result = executor.run("sh -lc 'printf %s \"$HOME\"'", host=host, retries=retries)
    home = result.stdout.strip()
    return home or "/tmp"


def normalize_path(path: str) -> str:
    return path.rstrip("/") or "/"

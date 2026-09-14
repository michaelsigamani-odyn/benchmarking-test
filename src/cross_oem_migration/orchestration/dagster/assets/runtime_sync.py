import shlex
from pathlib import Path
from typing import Any, Dict

from dagster import AssetExecutionContext, MetadataValue, asset

from ....remote_paths import resolve_remote_root
from ..resources import ExecutorResource, SettingsResource
from .preflight import source_gpu_preflight, target_gpu_preflight


SCRIPT_DIRS = ("scripts",)
ROOT_FILES = ("requirements.txt",)


@asset(group_name="control", deps=[source_gpu_preflight], description="Sync runtime scripts and requirements to source host.")
def source_runtime_scripts_synced(context: AssetExecutionContext, settings: SettingsResource, executor: ExecutorResource) -> Dict[str, Any]:
    cfg = settings.get()
    payload = sync_runtime_for_host(cfg, executor.get(cfg), cfg.source_host)
    context.add_output_metadata({"host": cfg.source_host, "remote_root": payload["remote_root"], "synced_items": MetadataValue.json(payload["synced_items"])})
    return payload


@asset(group_name="control", deps=[target_gpu_preflight], description="Sync runtime scripts and requirements to target host.")
def target_runtime_scripts_synced(context: AssetExecutionContext, settings: SettingsResource, executor: ExecutorResource) -> Dict[str, Any]:
    cfg = settings.get()
    payload = sync_runtime_for_host(cfg, executor.get(cfg), cfg.target_host)
    context.add_output_metadata({"host": cfg.target_host, "remote_root": payload["remote_root"], "synced_items": MetadataValue.json(payload["synced_items"])})
    return payload


def sync_runtime_for_host(settings, executor, host: str) -> Dict[str, Any]:
    remote_root = resolve_remote_root(executor, host, settings.remote_root, settings.command_retries)
    synced_items = copy_runtime_payloads(settings.local_root, remote_root, host, executor, settings.command_retries)
    maybe_install_requirements(settings, executor, host, remote_root)
    return {"host": host, "remote_root": remote_root, "synced_items": synced_items}


def copy_runtime_payloads(local_root: str, remote_root: str, host: str, executor, retries: int) -> list[str]:
    local_path = Path(local_root)
    copied = copy_root_files(local_path, remote_root, host, executor, retries)
    return copied + copy_script_dirs(local_path, remote_root, host, executor, retries)


def copy_root_files(local_root: Path, remote_root: str, host: str, executor, retries: int) -> list[str]:
    copied: list[str] = []
    for name in ROOT_FILES:
        source = local_root / name
        if not source.exists():
            continue
        executor.copy(str(source), f"{host}:{remote_root}/", retries=retries)
        copied.append(name)
    return copied


def copy_script_dirs(local_root: Path, remote_root: str, host: str, executor, retries: int) -> list[str]:
    copied: list[str] = []
    for name in SCRIPT_DIRS:
        source = local_root / name
        if not source.exists():
            continue
        executor.run(f"mkdir -p {shlex.quote(remote_root)}", host=host, retries=retries)
        executor.copy(str(source), f"{host}:{remote_root}/", recursive=True, retries=retries)
        copied.append(name)
    return copied


def maybe_install_requirements(settings, executor, host: str, remote_root: str) -> None:
    machine = settings.machine_for_host(host)
    if machine and machine.execution_mode == "docker":
        return
    python_cmd = settings.host_python_cmd_overrides.get(host) or (machine.python_cmd if machine else settings.source_python_cmd)
    command = requirements_install_command(python_cmd, remote_root)
    if machine and machine.torch_install_command:
        command = f"{command} && {machine.torch_install_command}"
    executor.run(command, host=host, retries=settings.command_retries, timeout_seconds=settings.command_timeout_seconds, operation="runtime_sync_install")


def requirements_install_command(python_cmd: str, remote_root: str) -> str:
    quoted_python = shlex.quote(python_cmd)
    requirements = shlex.quote(f"{remote_root}/requirements.txt")
    detect = f"IS_VENV=$({quoted_python} -c \"import sys; print(1 if sys.prefix != sys.base_prefix else 0)\")"
    ensurepip = f"{quoted_python} -m ensurepip --upgrade >/dev/null 2>&1 || true"
    venv = f"{quoted_python} -m pip install -U pip && {quoted_python} -m pip install -r {requirements}"
    system = f"{quoted_python} -m pip install --user --break-system-packages -U pip && {quoted_python} -m pip install --user --break-system-packages -r {requirements}"
    return f"{ensurepip}; {detect}; if [ \"$IS_VENV\" = \"1\" ]; then {venv}; else {system}; fi"

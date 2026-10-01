"""Dagster resources: this file (and assets/, checks.py, definitions.py)
is the ONLY part of the codebase allowed to `import dagster` (ask #3).
Everything a resource does is delegate to the framework-agnostic classes
in config/, execution/, hardware/, transfer/, workloads/, data/ -- so
those packages stay importable, testable, and reusable from a plain
script, a notebook, or a different orchestrator entirely.
"""
from pathlib import Path
from typing import Optional

from dagster import ConfigurableResource
from pydantic import Field

from ...config import PortabilitySettings, load_settings
from ...data.filesystem import LocalFilesystemArtifactStore, LocalFilesystemDatasetProvider
from ...data.metrics_db import RunMetricsDatabase
from ...execution.ssh import SSHExecutor
from ...hardware import get_adapter
from ...transfer import get_backend


class SettingsResource(ConfigurableResource):
    """Loads configs/run.json + configs/machines.json once per run.
    Wrapping `load_settings()` in a resource (rather than calling it at
    import time, as the original module-level-ish pattern effectively
    did) means tests can inject a different config_dir per test."""

    def get(self) -> PortabilitySettings:
        return load_settings()


class ExecutorResource(ConfigurableResource):
    """Executes commands on training hosts with safe defaults and optional run-time overrides.

    For stakeholders: this controls how quickly we fail on unreachable hosts and whether we allow
    password fallback or enforce key-only SSH during production runs.
    """

    connect_timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=300,
        description="Optional SSH connect-timeout override. Leave empty to use the environment setting.",
    )
    force_key_auth: bool = Field(
        default=False,
        description="If true, always use SSH keys and ignore configured passwords.",
    )
    ssh_password_override: Optional[str] = Field(
        default=None,
        description="Optional emergency password override for this run only. Keep empty for key-based auth.",
    )

    def _password(self, settings: PortabilitySettings) -> Optional[str]:
        if self.force_key_auth:
            return None
        return self.ssh_password_override if self.ssh_password_override is not None else settings.ssh_password

    def _connect_timeout(self, settings: PortabilitySettings) -> int:
        return int(self.connect_timeout_seconds or settings.ssh_connect_timeout_seconds)

    def get(self, settings: PortabilitySettings) -> SSHExecutor:
        return SSHExecutor(ssh_password=self._password(settings), connect_timeout_seconds=self._connect_timeout(settings))


class HardwareResource(ConfigurableResource):
    """Thin pass-through to hardware.get_adapter -- exists as a resource
    so assets don't import hardware.registry directly, keeping the
    dependency direction one-way (orchestration depends on hardware, not
    the reverse)."""

    def adapter_for(self, vendor: str):
        return get_adapter(vendor)


class TransferResource(ConfigurableResource):
    def get(self, settings: PortabilitySettings, executor: SSHExecutor):
        return get_backend(settings.transfer.backend, executor, settings, settings.remote_root)


class DataResource(ConfigurableResource):
    def dataset_provider(self, settings: PortabilitySettings, executor: SSHExecutor) -> LocalFilesystemDatasetProvider:
        return LocalFilesystemDatasetProvider(executor, settings.local_root, settings.remote_root, settings.command_retries)

    def artifact_store(self, settings: PortabilitySettings, executor: SSHExecutor) -> LocalFilesystemArtifactStore:
        return LocalFilesystemArtifactStore(executor, settings.local_root, settings.remote_root, settings.run_id, settings.command_retries)

    def metrics_db(self, settings: PortabilitySettings) -> RunMetricsDatabase:
        return RunMetricsDatabase(Path(settings.local_root) / "artifacts" / "run_metrics.sqlite")

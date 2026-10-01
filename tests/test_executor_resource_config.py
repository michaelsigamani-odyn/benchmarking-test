from dataclasses import dataclass

import pytest


@dataclass
class _SettingsStub:
    ssh_password: str | None
    ssh_connect_timeout_seconds: int


def test_executor_resource_uses_settings_by_default():
    pytest.importorskip("dagster")
    from src.cross_oem_migration.orchestration.dagster.resources import ExecutorResource

    executor = ExecutorResource().get(_SettingsStub("from-settings", 21))
    assert executor._ssh_password == "from-settings"
    assert executor._connect_timeout_seconds == 21


def test_executor_resource_can_force_key_auth():
    pytest.importorskip("dagster")
    from src.cross_oem_migration.orchestration.dagster.resources import ExecutorResource

    executor = ExecutorResource(force_key_auth=True).get(_SettingsStub("from-settings", 21))
    assert executor._ssh_password is None


def test_executor_resource_allows_per_run_overrides():
    pytest.importorskip("dagster")
    from src.cross_oem_migration.orchestration.dagster.resources import ExecutorResource

    resource = ExecutorResource(connect_timeout_seconds=9, ssh_password_override="override")
    executor = resource.get(_SettingsStub("from-settings", 21))
    assert executor._ssh_password == "override"
    assert executor._connect_timeout_seconds == 9

import pytest

from jaxft import device_transfer as dt


def test_transfer_roundtrip_is_explicit_and_correct():
    transfer = dt.validate_transfer_roundtrip()
    assert transfer["roundtrip_ok"] and transfer["sum_ok"] and transfer["speed_ok"]
    assert transfer["jax_put_mbps"] > 0 and transfer["jax_get_mbps"] > 0 and transfer["transfer_floor_mbps"] > 0
    assert transfer["transfer_floor_backend"] in {"mooncake", "tcp"}


def test_transfer_speed_metrics_prefers_mooncake(monkeypatch):
    monkeypatch.setattr(dt, "_time_device_put", lambda *_: 2.0)
    monkeypatch.setattr(dt, "_time_device_get", lambda *_: 1.0)
    monkeypatch.setattr(dt, "_time_mooncake_transfer", lambda *_: 4.0)
    monkeypatch.setattr(dt, "_time_tcp_transfer", lambda *_: 6.0)
    speeds = dt.transfer_speed_metrics()
    assert speeds["transfer_floor_backend"] == "mooncake"
    assert speeds["mooncake_floor_mbps"] == speeds["transfer_floor_mbps"]
    assert speeds["tcp_floor_mbps"] is None
    assert speeds["transfer_floor_fallback_reason"] is None


def test_transfer_speed_metrics_falls_back_to_tcp(monkeypatch):
    monkeypatch.setattr(dt, "_time_device_put", lambda *_: 2.0)
    monkeypatch.setattr(dt, "_time_device_get", lambda *_: 1.0)
    monkeypatch.setattr(dt, "_time_mooncake_transfer", lambda *_: (_ for _ in ()).throw(RuntimeError("mooncake unavailable")))
    monkeypatch.setattr(dt, "_time_tcp_transfer", lambda *_: 5.0)
    speeds = dt.transfer_speed_metrics()
    assert speeds["transfer_floor_backend"] == "tcp"
    assert speeds["tcp_floor_mbps"] == speeds["transfer_floor_mbps"]
    assert speeds["mooncake_floor_mbps"] is None
    assert "mooncake unavailable" in str(speeds["transfer_floor_fallback_reason"])


def test_dagster_materializes_transfer_validation_asset():
    dg = pytest.importorskip("dagster")
    import dagster_jax_portability as djp

    result = dg.materialize([djp.jax_data_transfer_validation])
    assert result.success


def test_report_depends_on_transfer_validation():
    pytest.importorskip("dagster")
    import dagster_jax_portability as djp

    report_key = next(iter(djp.jax_portability_report.keys))
    transfer_key = next(iter(djp.jax_data_transfer_validation.keys))
    assert transfer_key in djp.jax_portability_report.asset_deps[report_key]


def test_transfer_asset_hard_fails_when_validation_fails(monkeypatch):
    dg = pytest.importorskip("dagster")
    import dagster_jax_portability as djp

    monkeypatch.setattr(djp, "validate_transfer_roundtrip", lambda: {"roundtrip_ok": False, "sum_ok": True, "speed_ok": True})
    result = dg.materialize([djp.jax_data_transfer_validation], raise_on_error=False)
    assert not result.success

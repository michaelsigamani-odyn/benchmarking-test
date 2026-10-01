# Session Results

## Main outcomes
- JAX transfer validation now prefers a Mooncake floor benchmark and falls back to TCP when Mooncake runtime is unavailable.
- `jax_portability_report` is hard-gated by `jax_data_transfer_validation` in Dagster.
- Executor resource now has configurable, production-safe SSH controls (`connect_timeout_seconds`, `force_key_auth`, `ssh_password_override`).

## Validation status
- Pytest: `9 passed` for `tests/test_jax_data_transfer.py` and `tests/test_executor_resource_config.py`.
- Dagster validation asset materialized successfully: `jax_data_transfer_validation` run result `success True`.

## Latest benchmark report
```json
{
  "device_token_shape": [3, 4],
  "host_token_shape": [3, 4],
  "jax_get_mbps": 697167.7520531198,
  "jax_put_mbps": 138567.9636695907,
  "mooncake_floor_mbps": null,
  "roundtrip_ok": true,
  "speed_ok": true,
  "sum_ok": true,
  "tcp_floor_mbps": 2709.851029655606,
  "transfer_floor_backend": "tcp",
  "transfer_floor_fallback_reason": "mooncake.engine is not installed",
  "transfer_floor_mbps": 2709.851029655606
}
```

-- =========================================================
-- GPU telemetry reconciliation extract (machine + GPU level)
--
-- Run with:
--   bq query --nouse_legacy_sql < scripts/db/gpu_telemetry_reconciliation_v3.sql
-- =========================================================

-- 1) Authoritative machine registry (prodv2)
SELECT
  CURRENT_TIMESTAMP() AS extracted_at,
  host,
  machine_name,
  provider,
  plane,
  region,
  environment,
  machine_status,
  active,
  expected_gpu_count,
  gpu_vendors,
  gpu_models,
  registry_source,
  inventory_last_seen_at,
  machine_last_heartbeat
FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3`
ORDER BY plane, provider, host;


-- 2) Machine-level reporting reconciliation
SELECT
  evaluated_at,
  host,
  machine_name,
  provider,
  plane,
  region,
  machine_status,
  active,
  expected_gpu_count,
  reporting_gpu_count,
  stale_gpu_count,
  not_reporting_gpu_count,
  unknown_gpu_count,
  reporting_coverage_pct,
  reporting_or_stale_coverage_pct,
  machine_freshness_class,
  machine_freshness_reason,
  machine_sample_age_seconds,
  has_gpu_fault,
  last_sample_timestamp
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
ORDER BY plane, provider, host;


-- 3) GPU-level reporting reconciliation
SELECT
  host,
  machine_name,
  provider,
  plane,
  region,
  gpu_index_expected,
  gpu_key_expected,
  gpu_vendor_expected,
  gpu_model_expected,
  sample_timestamp,
  sample_age_seconds,
  gpu_index,
  gpu_key,
  gpu_vendor,
  gpu_model,
  gpu_status,
  freshness_class,
  freshness_reason,
  gpu_utilization_pct,
  gpu_memory_used_mib,
  gpu_memory_total_mib,
  gpu_memory_utilization_pct,
  temperature_celsius,
  power_watts,
  util_missing_reason,
  power_missing_reason,
  temperature_missing_reason,
  memory_used_missing_reason,
  memory_total_missing_reason,
  telemetry_backend,
  source_name
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_reporting_v3`
ORDER BY plane, provider, host, COALESCE(gpu_key_expected, CONCAT('idx:', CAST(COALESCE(gpu_index_expected, -1) AS STRING)));


-- 4) Provider catalog coverage (external baseline)
SELECT
  provider,
  sku_count,
  rate_rows,
  min_hourly_rate_usd,
  max_hourly_rate_usd,
  latest_rate_updated_at
FROM `inbound-dahlia-507808-g1.fleet_ops.provider_catalog_v1`
ORDER BY provider;


-- 5) Fleet summary
SELECT *
FROM `inbound-dahlia-507808-g1.fleet_ops.fleet_reporting_summary_v3`;

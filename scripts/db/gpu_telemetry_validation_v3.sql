-- =========================================================
-- GPU telemetry rollout validation query pack (Tests A-G)
--
-- Run with:
--   bq query --nouse_legacy_sql < scripts/db/gpu_telemetry_validation_v3.sql
--
-- This script is read-only and returns result sets for each test.
-- =========================================================

DECLARE reporting_threshold_s INT64 DEFAULT 180;  -- <3 minutes
DECLARE stale_threshold_s INT64 DEFAULT 600;      -- 3-10 minutes

-- ---------------------------------------------------------
-- Test A: London edge freshness and coverage
-- ---------------------------------------------------------
SELECT
  'A_london_edge_freshness' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  COUNT(*) AS machines_in_scope,
  COUNTIF(machine_freshness_class = 'Reporting') AS machines_reporting,
  COUNTIF(machine_freshness_class = 'Stale') AS machines_stale,
  COUNTIF(machine_freshness_class = 'Not reporting') AS machines_not_reporting,
  COUNTIF(machine_freshness_class = 'Unknown') AS machines_unknown,
  SUM(expected_gpu_count) AS expected_gpus,
  SUM(reporting_gpu_count) AS reporting_gpus,
  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS reporting_coverage_pct,
  MAX(machine_sample_age_seconds) AS max_machine_sample_age_seconds
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
WHERE LOWER(plane) = 'edge'
  AND (
    LOWER(region) LIKE '%london%'
    OR LOWER(region) LIKE '%edge%'
  );


-- ---------------------------------------------------------
-- Test B: prodv2 cloud freshness and coverage
-- ---------------------------------------------------------
SELECT
  'B_prodv2_cloud_freshness' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  COUNT(*) AS machines_in_scope,
  COUNTIF(machine_freshness_class = 'Reporting') AS machines_reporting,
  COUNTIF(machine_freshness_class = 'Stale') AS machines_stale,
  COUNTIF(machine_freshness_class = 'Not reporting') AS machines_not_reporting,
  COUNTIF(machine_freshness_class = 'Unknown') AS machines_unknown,
  SUM(expected_gpu_count) AS expected_gpus,
  SUM(reporting_gpu_count) AS reporting_gpus,
  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS reporting_coverage_pct,
  MAX(machine_sample_age_seconds) AS max_machine_sample_age_seconds
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
WHERE LOWER(plane) = 'cloud';


-- ---------------------------------------------------------
-- Test C: Mac independence (laptop sampler no longer primary source)
-- ---------------------------------------------------------
WITH recent AS (
  SELECT
    SAFE_CAST(sample_ts AS TIMESTAMP) AS sample_ts,
    sampler_run_id
  FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1`
  WHERE SAFE_CAST(sample_ts AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
)
SELECT
  'C_mac_independence' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  COUNT(*) AS rows_24h,
  COUNTIF(sampler_run_id LIKE 'edge-agent:%') AS host_agent_rows,
  COUNTIF(REGEXP_CONTAINS(COALESCE(sampler_run_id, ''), r'^edge_\d{8}T\d{6}Z_')) AS laptop_sampler_rows,
  MAX(IF(sampler_run_id LIKE 'edge-agent:%', sample_ts, NULL)) AS latest_host_agent_ts,
  MAX(IF(REGEXP_CONTAINS(COALESCE(sampler_run_id, ''), r'^edge_\d{8}T\d{6}Z_'), sample_ts, NULL)) AS latest_laptop_sampler_ts,
  (
    COUNTIF(sampler_run_id LIKE 'edge-agent:%') > 0
    AND (
      COUNTIF(REGEXP_CONTAINS(COALESCE(sampler_run_id, ''), r'^edge_\d{8}T\d{6}Z_')) = 0
      OR MAX(IF(sampler_run_id LIKE 'edge-agent:%', sample_ts, NULL)) >= MAX(IF(REGEXP_CONTAINS(COALESCE(sampler_run_id, ''), r'^edge_\d{8}T\d{6}Z_'), sample_ts, NULL))
    )
  ) AS host_agent_is_primary
FROM recent;


-- ---------------------------------------------------------
-- Test D: collector restart/crash indicator
-- ---------------------------------------------------------
SELECT
  'D_collector_restarts' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  COUNT(*) AS restart_alert_rows,
  ARRAY_AGG(STRUCT(host, distinct_agent_instances_30m, agent_instances, last_sample_timestamp) ORDER BY host LIMIT 50) AS sample_alerts
FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_collector_restarts_v1`;


-- ---------------------------------------------------------
-- Test E: retry/dedup health (duplicate natural keys)
-- ---------------------------------------------------------
WITH raw_dups AS (
  SELECT COUNT(*) AS duplicate_groups
  FROM (
    SELECT
      COALESCE(LOWER(TRIM(host)), '_unknown_host_') AS host,
      SAFE_CAST(sample_ts AS TIMESTAMP) AS sample_ts,
      COALESCE(SAFE_CAST(gpu_index AS INT64), -1) AS gpu_index,
      COALESCE(LOWER(TRIM(vendor)), '_unknown_vendor_') AS vendor
    FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1`
    GROUP BY host, sample_ts, gpu_index, vendor
    HAVING COUNT(*) > 1
  )
), dedup_dups AS (
  SELECT COUNT(*) AS duplicate_groups
  FROM (
    SELECT
      host,
      sample_timestamp,
      COALESCE(gpu_key, CONCAT('idx:', CAST(COALESCE(gpu_index, -1) AS STRING))) AS gpu_identity
    FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_telemetry_latest_v3`
    GROUP BY host, sample_timestamp, gpu_identity
    HAVING COUNT(*) > 1
  )
)
SELECT
  'E_retry_and_dedup' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  raw_dups.duplicate_groups AS raw_duplicate_groups,
  dedup_dups.duplicate_groups AS latest_view_duplicate_groups,
  (raw_dups.duplicate_groups = 0 AND dedup_dups.duplicate_groups = 0) AS dedup_pass
FROM raw_dups, dedup_dups;


-- ---------------------------------------------------------
-- Test F: fleet reconciliation (machine-level + GPU-level)
-- ---------------------------------------------------------
SELECT
  'F_fleet_reconciliation_machine' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  plane,
  provider,
  COUNT(*) AS machine_count,
  SUM(expected_gpu_count) AS expected_gpu_count,
  SUM(reporting_gpu_count) AS reporting_gpu_count,
  SUM(stale_gpu_count) AS stale_gpu_count,
  SUM(not_reporting_gpu_count) AS not_reporting_gpu_count,
  SUM(unknown_gpu_count) AS unknown_gpu_count,
  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS reporting_coverage_pct,
  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count + stale_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS reporting_or_stale_coverage_pct
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
GROUP BY plane, provider
ORDER BY plane, provider;

SELECT
  'F_fleet_reconciliation_gpu' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  plane,
  provider,
  freshness_class,
  COUNT(*) AS gpu_rows
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_reporting_v3`
GROUP BY plane, provider, freshness_class
ORDER BY plane, provider, freshness_class;


-- ---------------------------------------------------------
-- Test G: dashboard/readiness checks
-- ---------------------------------------------------------
WITH checks AS (
  SELECT 'fleet_ops.machine_reporting_v3' AS object_name, COUNT(*) AS row_count
  FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
  UNION ALL
  SELECT 'fleet_ops.machine_gpu_reporting_v3', COUNT(*)
  FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_reporting_v3`
  UNION ALL
  SELECT 'fleet_ops.fleet_reporting_summary_v3', COUNT(*)
  FROM `inbound-dahlia-507808-g1.fleet_ops.fleet_reporting_summary_v3`
  UNION ALL
  SELECT 'clean_ops.machine_gpu_telemetry_prodv2_v3', COUNT(*)
  FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
  UNION ALL
  SELECT 'clean_ops.fact_gpu_telemetry_backfill_candidate_v1', COUNT(*)
  FROM `inbound-dahlia-507808-g1.clean_ops.fact_gpu_telemetry_backfill_candidate_v1`
)
SELECT
  'G_dashboard_readiness_row_counts' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  *
FROM checks
ORDER BY object_name;

SELECT
  'G_dashboard_readiness_null_keys' AS test_id,
  CURRENT_TIMESTAMP() AS evaluated_at,
  COUNTIF(host IS NULL OR host = '') AS null_or_empty_host_rows,
  COUNTIF(sample_timestamp IS NULL) AS null_sample_timestamp_rows,
  COUNTIF(gpu_index IS NULL AND gpu_key IS NULL) AS null_gpu_identity_rows
FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`;


-- ---------------------------------------------------------
-- Alert snapshot summary
-- ---------------------------------------------------------
SELECT
  'alert_snapshot' AS section,
  CURRENT_TIMESTAMP() AS evaluated_at,
  (SELECT alert_triggered FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_ingest_stop_v1` LIMIT 1) AS ingest_stop_alert,
  (SELECT COUNT(*) FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_stale_or_not_reporting_v1`) AS stale_or_not_reporting_alert_rows,
  (SELECT COUNT(*) FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_collector_restarts_v1`) AS collector_restart_alert_rows,
  (SELECT COUNT(*) FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_faults_sustained_v1`) AS sustained_fault_alert_rows,
  (SELECT alert_triggered FROM `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_coverage_drop_v1` LIMIT 1) AS coverage_drop_alert;

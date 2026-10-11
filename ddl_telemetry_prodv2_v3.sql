-- =========================================================
-- GPU telemetry prodv2 v3 model
--
-- Goals
-- - Build fleet inventory from authoritative registries/snapshots
-- - Unify edge + cloud GPU telemetry into one canonical prodv2 model
-- - Classify freshness using required classes:
--     Reporting (<3m), Stale (3-10m), Not reporting (>10m), Unknown
-- - Preserve null metrics with explicit reasons
-- - Provide alert-ready views and reconciliation outputs
--
-- Project is pinned to inbound-dahlia-507808-g1 to match existing assets.
-- =========================================================

-- 0) Stable datasets
CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.clean_ops`
OPTIONS (location = 'EU');

CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.fleet_ops`
OPTIONS (location = 'EU');


-- 1) Latest per-row-key snapshot view from pg_state_snapshot_v1
--    (authoritative source for control-plane node/gpu state exported from Postgres)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.raw_ops.pg_state_snapshot_latest_rows_v1` AS
WITH parsed AS (
  SELECT
    table_name,
    row_pk,
    SAFE_CAST(captured_at AS TIMESTAMP) AS captured_at,
    COALESCE(SAFE_CAST(is_deleted AS BOOL), FALSE) AS is_deleted,
    SAFE.PARSE_JSON(row_json) AS row_json_obj,
    row_hash
  FROM `inbound-dahlia-507808-g1.raw_ops.pg_state_snapshot_v1`
), ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY table_name, row_pk
      ORDER BY captured_at DESC, COALESCE(row_hash, '') DESC
    ) AS row_num
  FROM parsed
)
SELECT * EXCEPT (row_num)
FROM ranked
WHERE row_num = 1
  AND is_deleted = FALSE
  AND row_json_obj IS NOT NULL;


-- 2) Control-plane node and GPU inventory snapshots (authoritative cloud registry source)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.prodv2_nodes_snapshot_latest_v1` AS
SELECT
  LOWER(TRIM(JSON_VALUE(row_json_obj, '$.id'))) AS node_id,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.id')), '') AS node_id_raw,
  LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.provider')), '')) AS provider,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.platform')), '') AS platform,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.region')), '') AS region,
  LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.status')), '')) AS node_status,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.is_listed') AS BOOL) AS is_listed,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.last_heartbeat') AS TIMESTAMP) AS last_heartbeat,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.created_at') AS TIMESTAMP) AS created_at,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.updated_at') AS TIMESTAMP) AS updated_at,
  captured_at AS snapshot_captured_at
FROM `inbound-dahlia-507808-g1.raw_ops.pg_state_snapshot_latest_rows_v1`
WHERE table_name = 'public.nodes'
  AND NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.id')), '') IS NOT NULL;


CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.prodv2_gpu_inventory_snapshot_latest_v1` AS
SELECT
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.gpu_key')), '') AS gpu_key,
  LOWER(TRIM(JSON_VALUE(row_json_obj, '$.node_id'))) AS node_id,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.device_index') AS INT64) AS gpu_index,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.gpu_uuid')), '') AS gpu_uuid,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.model_name')), '') AS gpu_model,
  LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.vendor')), '')) AS vendor,
  NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.accelerator_architecture')), '') AS accelerator_architecture,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.memory_total_mib') AS FLOAT64) AS gpu_memory_total_mib,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.is_healthy') AS BOOL) AS is_healthy,
  LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.status')), '')) AS inventory_status,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.last_seen_at') AS TIMESTAMP) AS last_seen_at,
  SAFE_CAST(JSON_VALUE(row_json_obj, '$.updated_at') AS TIMESTAMP) AS updated_at,
  captured_at AS snapshot_captured_at
FROM `inbound-dahlia-507808-g1.raw_ops.pg_state_snapshot_latest_rows_v1`
WHERE table_name = 'public.gpu_inventory'
  AND NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.gpu_key')), '') IS NOT NULL;


-- 3) External/cloud provider catalog from authoritative baseline rates snapshot
--    (provider catalog coverage when host-level external machine inventory is unavailable)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.provider_catalog_v1` AS
WITH rates AS (
  SELECT
    LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.provider')), '')) AS provider,
    NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.sku')), '') AS sku,
    LOWER(NULLIF(TRIM(JSON_VALUE(row_json_obj, '$.intake_type')), '')) AS intake_type,
    SAFE_CAST(JSON_VALUE(row_json_obj, '$.usd_per_hour') AS FLOAT64) AS usd_per_hour,
    SAFE_CAST(JSON_VALUE(row_json_obj, '$.updated_at') AS TIMESTAMP) AS updated_at
  FROM `inbound-dahlia-507808-g1.raw_ops.pg_state_snapshot_latest_rows_v1`
  WHERE table_name = 'public.gpu_baseline_rates'
)
SELECT
  provider,
  COUNT(DISTINCT sku) AS sku_count,
  COUNT(*) AS rate_rows,
  ROUND(MIN(usd_per_hour), 4) AS min_hourly_rate_usd,
  ROUND(MAX(usd_per_hour), 4) AS max_hourly_rate_usd,
  MAX(updated_at) AS latest_rate_updated_at
FROM rates
WHERE provider IS NOT NULL
GROUP BY provider;


-- 4) Authoritative prodv2 machine registry (edge + cloud)
--    - cloud from control-plane nodes/gpu_inventory snapshots
--    - edge from edge_machine_registry_v1
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` AS
WITH cloud_registry AS (
  SELECT
    n.node_id AS host,
    COALESCE(NULLIF(TRIM(n.node_id_raw), ''), n.node_id) AS machine_name,
    COALESCE(NULLIF(TRIM(n.provider), ''), 'odyn') AS provider,
    'cloud' AS plane,
    COALESCE(NULLIF(TRIM(n.region), ''), 'unknown') AS region,
    'prodv2' AS environment,
    COALESCE(n.node_status, 'unknown') AS machine_status,
    (n.node_status IN ('online', 'preparing')) AS active,
    COUNTIF(g.gpu_key IS NOT NULL) AS expected_gpu_count,
    STRING_AGG(DISTINCT COALESCE(NULLIF(TRIM(g.vendor), ''), 'unknown'), ', ' ORDER BY COALESCE(NULLIF(TRIM(g.vendor), ''), 'unknown')) AS gpu_vendors,
    STRING_AGG(DISTINCT COALESCE(NULLIF(TRIM(g.gpu_model), ''), 'unknown'), ', ' ORDER BY COALESCE(NULLIF(TRIM(g.gpu_model), ''), 'unknown')) AS gpu_models,
    MAX(g.last_seen_at) AS inventory_last_seen_at,
    MAX(n.last_heartbeat) AS machine_last_heartbeat,
    'raw_ops.pg_state_snapshot_v1(public.nodes/public.gpu_inventory)' AS registry_source,
    20 AS source_rank
  FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_nodes_snapshot_latest_v1` n
  LEFT JOIN `inbound-dahlia-507808-g1.clean_ops.prodv2_gpu_inventory_snapshot_latest_v1` g
    ON g.node_id = n.node_id
  GROUP BY
    host, machine_name, provider, plane, region, environment, machine_status, active, registry_source, source_rank
), edge_registry AS (
  SELECT
    LOWER(TRIM(host)) AS host,
    COALESCE(NULLIF(TRIM(display_name), ''), TRIM(host)) AS machine_name,
    'edge' AS provider,
    'edge' AS plane,
    COALESCE(NULLIF(TRIM(site), ''), 'london-edge') AS region,
    'prodv2' AS environment,
    'online' AS machine_status,
    TRUE AS active,
    COALESCE(SAFE_CAST(expected_gpus AS INT64), 0) AS expected_gpu_count,
    LOWER(NULLIF(TRIM(vendor), '')) AS gpu_vendors,
    NULL AS gpu_models,
    NULL AS inventory_last_seen_at,
    NULL AS machine_last_heartbeat,
    'clean_ops.edge_machine_registry_v1' AS registry_source,
    10 AS source_rank
  FROM `inbound-dahlia-507808-g1.clean_ops.edge_machine_registry_v1`
), unioned AS (
  SELECT * FROM edge_registry
  UNION ALL
  SELECT * FROM cloud_registry
), deduped AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY host
      ORDER BY source_rank ASC, expected_gpu_count DESC, machine_name ASC
    ) AS row_num
  FROM unioned
)
SELECT * EXCEPT (source_rank, row_num)
FROM deduped
WHERE row_num = 1;


-- 5) Expected GPU catalog per machine (machine-level and GPU-level reconciliation base)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.prodv2_expected_gpu_catalog_v3` AS
WITH edge_expected AS (
  SELECT
    r.host,
    idx AS gpu_index_expected,
    NULL AS gpu_key_expected,
    LOWER(NULLIF(TRIM(r.gpu_vendors), '')) AS gpu_vendor_expected,
    NULL AS gpu_model_expected,
    'edge_registry_expected_count' AS expected_source
  FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` r,
  UNNEST(GENERATE_ARRAY(0, IFNULL(r.expected_gpu_count, 0) - 1)) AS idx
  WHERE r.plane = 'edge'
), cloud_expected AS (
  SELECT
    g.node_id AS host,
    g.gpu_index AS gpu_index_expected,
    g.gpu_key AS gpu_key_expected,
    g.vendor AS gpu_vendor_expected,
    g.gpu_model AS gpu_model_expected,
    'gpu_inventory_snapshot' AS expected_source
  FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_gpu_inventory_snapshot_latest_v1` g
)
SELECT * FROM edge_expected
UNION ALL
SELECT * FROM cloud_expected;


-- 6) Deduped raw edge stream
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.raw_ops.machine_gpu_telemetry_samples_dedup_v3` AS
WITH scored AS (
  SELECT
    s.*,
    (
      IF(s.gpu_index IS NULL, 0, 1)
      + IF(s.gpu_name IS NULL, 0, 1)
      + IF(s.util_gpu_pct IS NULL, 0, 1)
      + IF(s.vram_pct IS NULL, 0, 1)
      + IF(s.mem_total_mib IS NULL, 0, 1)
      + IF(s.mem_used_mib IS NULL, 0, 1)
      + IF(s.power_w IS NULL, 0, 1)
      + IF(s.temp_c IS NULL, 0, 1)
      + IF(s.driver_version IS NULL, 0, 1)
      + IF(s.ts_backend IS NULL, 0, 1)
      + IF(s.agent_version IS NULL, 0, 1)
      + IF(s.reachable IS NULL, 0, 1)
    ) AS quality_score
  FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1` s
), ranked AS (
  SELECT
    scored.*,
    ROW_NUMBER() OVER (
      PARTITION BY
        COALESCE(LOWER(TRIM(host)), '_unknown_host_'),
        SAFE_CAST(sample_ts AS TIMESTAMP),
        COALESCE(SAFE_CAST(gpu_index AS INT64), -1),
        COALESCE(LOWER(TRIM(vendor)), '_unknown_vendor_')
      ORDER BY
        quality_score DESC,
        COALESCE(sampler_run_id, '') DESC,
        COALESCE(agent_version, '') DESC
    ) AS row_num
  FROM scored
)
SELECT * EXCEPT (quality_score, row_num)
FROM ranked
WHERE row_num = 1;


-- 7) Normalized telemetry: edge source
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_edge_v3` AS
SELECT
  SAFE_CAST(s.sample_ts AS TIMESTAMP) AS sample_timestamp,
  LOWER(TRIM(s.host)) AS host,
  NULL AS gpu_key,
  SAFE_CAST(s.gpu_index AS INT64) AS gpu_index,
  'edge' AS provider,
  'edge' AS plane,
  COALESCE(NULLIF(TRIM(s.site), ''), 'london-edge') AS region,
  LOWER(NULLIF(TRIM(s.vendor), '')) AS gpu_vendor,
  NULLIF(TRIM(s.gpu_name), '') AS gpu_model,
  NULLIF(TRIM(s.driver_version), '') AS gpu_driver_version,
  LOWER(NULLIF(TRIM(s.gpu_status), '')) AS gpu_status,
  ROUND(SAFE_CAST(s.util_gpu_pct AS FLOAT64), 2) AS gpu_utilization_pct,
  ROUND(SAFE_CAST(s.mem_used_mib AS FLOAT64), 2) AS gpu_memory_used_mib,
  ROUND(SAFE_CAST(s.mem_total_mib AS FLOAT64), 2) AS gpu_memory_total_mib,
  ROUND(SAFE_CAST(s.vram_pct AS FLOAT64), 2) AS gpu_memory_utilization_pct,
  ROUND(SAFE_CAST(s.power_w AS FLOAT64), 2) AS power_watts,
  ROUND(SAFE_CAST(s.temp_c AS FLOAT64), 2) AS temperature_celsius,
  ROUND(SAFE_CAST(s.load1 AS FLOAT64), 2) AS host_load_1m,
  SAFE_CAST(s.containers AS INT64) AS running_containers,
  SAFE_CAST(s.reachable AS BOOL) AS host_reachable,
  SAFE_CAST(s.vpn_online AS BOOL) AS vpn_online,
  NULLIF(TRIM(s.agent_version), '') AS collector_version,
  NULLIF(TRIM(s.ts_backend), '') AS telemetry_backend,
  NULLIF(TRIM(s.sampler_run_id), '') AS collector_run_id,
  SAFE_CAST(s.skipped AS BOOL) AS telemetry_skipped,
  'raw_ops.edge_gpu_samples_v1' AS source_name,

  CASE
    WHEN s.util_gpu_pct IS NOT NULL THEN NULL
    WHEN LOWER(COALESCE(s.gpu_status, '')) = 'fault' THEN 'gpu_fault'
    WHEN SAFE_CAST(s.reachable AS BOOL) IS FALSE THEN 'host_unreachable'
    WHEN SAFE_CAST(s.skipped AS BOOL) IS TRUE THEN 'fault_backoff_skip'
    ELSE 'metric_not_reported'
  END AS util_missing_reason,

  CASE
    WHEN s.power_w IS NOT NULL THEN NULL
    WHEN LOWER(COALESCE(s.gpu_status, '')) = 'fault' THEN 'gpu_fault'
    WHEN SAFE_CAST(s.reachable AS BOOL) IS FALSE THEN 'host_unreachable'
    WHEN SAFE_CAST(s.skipped AS BOOL) IS TRUE THEN 'fault_backoff_skip'
    ELSE 'metric_not_reported'
  END AS power_missing_reason,

  CASE
    WHEN s.temp_c IS NOT NULL THEN NULL
    WHEN LOWER(COALESCE(s.gpu_status, '')) = 'fault' THEN 'gpu_fault'
    WHEN SAFE_CAST(s.reachable AS BOOL) IS FALSE THEN 'host_unreachable'
    WHEN SAFE_CAST(s.skipped AS BOOL) IS TRUE THEN 'fault_backoff_skip'
    ELSE 'metric_not_reported'
  END AS temperature_missing_reason,

  CASE
    WHEN s.mem_used_mib IS NOT NULL THEN NULL
    WHEN LOWER(COALESCE(s.gpu_status, '')) = 'fault' THEN 'gpu_fault'
    ELSE 'metric_not_reported'
  END AS memory_used_missing_reason,

  CASE
    WHEN s.mem_total_mib IS NOT NULL THEN NULL
    WHEN LOWER(COALESCE(s.gpu_status, '')) = 'fault' THEN 'gpu_fault'
    ELSE 'metric_not_reported'
  END AS memory_total_missing_reason
FROM `inbound-dahlia-507808-g1.raw_ops.machine_gpu_telemetry_samples_dedup_v3` s
JOIN `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` r
  ON LOWER(TRIM(s.host)) = r.host
WHERE r.active = TRUE
  AND r.plane = 'edge'
  AND SAFE_CAST(s.sample_ts AS TIMESTAMP) IS NOT NULL;


-- 8) Normalized telemetry: cloud source (control-plane gpu_inventory snapshots)
--    Metrics unavailable in this source are kept NULL with explicit reasons.
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_cloud_v3` AS
SELECT
  COALESCE(g.last_seen_at, n.last_heartbeat) AS sample_timestamp,
  n.node_id AS host,
  g.gpu_key AS gpu_key,
  g.gpu_index AS gpu_index,
  COALESCE(NULLIF(TRIM(n.provider), ''), 'odyn') AS provider,
  'cloud' AS plane,
  COALESCE(NULLIF(TRIM(n.region), ''), 'unknown') AS region,
  COALESCE(NULLIF(TRIM(g.vendor), ''), 'unknown') AS gpu_vendor,
  COALESCE(NULLIF(TRIM(g.gpu_model), ''), 'unknown') AS gpu_model,
  NULL AS gpu_driver_version,
  CASE
    WHEN g.is_healthy IS TRUE AND COALESCE(g.inventory_status, 'available') <> 'unhealthy' THEN 'ok'
    WHEN g.is_healthy IS FALSE OR COALESCE(g.inventory_status, '') = 'unhealthy' THEN 'fault'
    ELSE 'unreadable'
  END AS gpu_status,
  CAST(NULL AS FLOAT64) AS gpu_utilization_pct,
  CAST(NULL AS FLOAT64) AS gpu_memory_used_mib,
  ROUND(SAFE_CAST(g.gpu_memory_total_mib AS FLOAT64), 2) AS gpu_memory_total_mib,
  CAST(NULL AS FLOAT64) AS gpu_memory_utilization_pct,
  CAST(NULL AS FLOAT64) AS power_watts,
  CAST(NULL AS FLOAT64) AS temperature_celsius,
  CAST(NULL AS FLOAT64) AS host_load_1m,
  CAST(NULL AS INT64) AS running_containers,
  (COALESCE(n.node_status, 'unknown') IN ('online', 'preparing')) AS host_reachable,
  CAST(NULL AS BOOL) AS vpn_online,
  CAST(NULL AS STRING) AS collector_version,
  'control_plane_gpu_inventory' AS telemetry_backend,
  CONCAT('pg_snapshot:', CAST(g.snapshot_captured_at AS STRING)) AS collector_run_id,
  FALSE AS telemetry_skipped,
  'raw_ops.pg_state_snapshot_v1/public.gpu_inventory' AS source_name,

  'not_available_in_gpu_inventory_snapshot' AS util_missing_reason,
  'not_available_in_gpu_inventory_snapshot' AS power_missing_reason,
  'not_available_in_gpu_inventory_snapshot' AS temperature_missing_reason,
  'not_available_in_gpu_inventory_snapshot' AS memory_used_missing_reason,
  CASE
    WHEN g.gpu_memory_total_mib IS NOT NULL THEN NULL
    ELSE 'not_reported_in_gpu_inventory_snapshot'
  END AS memory_total_missing_reason
FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_nodes_snapshot_latest_v1` n
JOIN `inbound-dahlia-507808-g1.clean_ops.prodv2_gpu_inventory_snapshot_latest_v1` g
  ON g.node_id = n.node_id
JOIN `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` r
  ON n.node_id = r.host
WHERE r.active = TRUE
  AND r.plane = 'cloud';


-- 9) Canonical prodv2 telemetry union (edge + cloud)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3` AS
SELECT * FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_edge_v3`
UNION ALL
SELECT * FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_cloud_v3`;


-- 10) Latest sample per machine+GPU identity
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_telemetry_latest_v3` AS
SELECT *
FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY
    host,
    COALESCE(gpu_key, CONCAT('idx:', CAST(COALESCE(gpu_index, -1) AS STRING)))
  ORDER BY sample_timestamp DESC, COALESCE(collector_run_id, '') DESC
) = 1;


-- 11) GPU-level reporting class (Reporting/Stale/Not reporting/Unknown)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_reporting_v3` AS
WITH expected AS (
  SELECT
    e.host,
    e.gpu_index_expected,
    e.gpu_key_expected,
    e.gpu_vendor_expected,
    e.gpu_model_expected,
    e.expected_source,
    r.machine_name,
    r.provider,
    r.plane,
    r.region,
    r.environment,
    r.active
  FROM `inbound-dahlia-507808-g1.fleet_ops.prodv2_expected_gpu_catalog_v3` e
  JOIN `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` r
    ON e.host = r.host
), joined AS (
  SELECT
    e.*,
    l.sample_timestamp,
    l.gpu_key,
    l.gpu_index,
    l.gpu_vendor,
    l.gpu_model,
    l.gpu_status,
    l.gpu_utilization_pct,
    l.gpu_memory_used_mib,
    l.gpu_memory_total_mib,
    l.gpu_memory_utilization_pct,
    l.power_watts,
    l.temperature_celsius,
    l.host_reachable,
    l.vpn_online,
    l.collector_version,
    l.telemetry_backend,
    l.source_name,
    l.util_missing_reason,
    l.power_missing_reason,
    l.temperature_missing_reason,
    l.memory_used_missing_reason,
    l.memory_total_missing_reason,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), l.sample_timestamp, SECOND) AS sample_age_seconds
  FROM expected e
  LEFT JOIN `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_telemetry_latest_v3` l
    ON l.host = e.host
   AND (
     (e.gpu_key_expected IS NOT NULL AND l.gpu_key = e.gpu_key_expected)
     OR (
       e.gpu_key_expected IS NULL
       AND COALESCE(l.gpu_index, -1) = COALESCE(e.gpu_index_expected, -1)
     )
   )
)
SELECT
  host,
  machine_name,
  provider,
  plane,
  region,
  environment,
  active,
  gpu_index_expected,
  gpu_key_expected,
  gpu_vendor_expected,
  gpu_model_expected,
  expected_source,
  sample_timestamp,
  sample_age_seconds,
  gpu_key,
  gpu_index,
  gpu_vendor,
  gpu_model,
  gpu_status,
  gpu_utilization_pct,
  gpu_memory_used_mib,
  gpu_memory_total_mib,
  gpu_memory_utilization_pct,
  power_watts,
  temperature_celsius,
  host_reachable,
  vpn_online,
  collector_version,
  telemetry_backend,
  source_name,
  util_missing_reason,
  power_missing_reason,
  temperature_missing_reason,
  memory_used_missing_reason,
  memory_total_missing_reason,
  CASE
    WHEN sample_timestamp IS NULL THEN 'Unknown'
    WHEN sample_age_seconds < 180 THEN 'Reporting'
    WHEN sample_age_seconds <= 600 THEN 'Stale'
    ELSE 'Not reporting'
  END AS freshness_class,
  CASE
    WHEN sample_timestamp IS NULL THEN 'never_reported_or_reconcile_failed'
    WHEN sample_age_seconds < 180 THEN 'fresh_within_3m'
    WHEN sample_age_seconds <= 600 THEN 'sample_3_to_10m_old'
    ELSE 'sample_older_than_10m'
  END AS freshness_reason
FROM joined;


-- 12) Machine-level reporting/coverage reconciliation
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3` AS
WITH per_gpu AS (
  SELECT
    host,
    COUNT(*) AS expected_gpu_count,
    COUNTIF(freshness_class = 'Reporting') AS reporting_gpu_count,
    COUNTIF(freshness_class = 'Stale') AS stale_gpu_count,
    COUNTIF(freshness_class = 'Not reporting') AS not_reporting_gpu_count,
    COUNTIF(freshness_class = 'Unknown') AS unknown_gpu_count,
    MAX(sample_timestamp) AS last_sample_timestamp,
    MAX(sample_age_seconds) AS max_gpu_sample_age_seconds,
    LOGICAL_OR(LOWER(COALESCE(gpu_status, '')) = 'fault') AS has_gpu_fault
  FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_reporting_v3`
  GROUP BY host
)
SELECT
  r.host,
  r.machine_name,
  r.provider,
  r.plane,
  r.region,
  r.environment,
  r.machine_status,
  r.active,

  COALESCE(p.expected_gpu_count, r.expected_gpu_count) AS expected_gpu_count,
  COALESCE(p.reporting_gpu_count, 0) AS reporting_gpu_count,
  COALESCE(p.stale_gpu_count, 0) AS stale_gpu_count,
  COALESCE(p.not_reporting_gpu_count, 0) AS not_reporting_gpu_count,
  COALESCE(p.unknown_gpu_count, 0) AS unknown_gpu_count,

  p.last_sample_timestamp,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), p.last_sample_timestamp, SECOND) AS machine_sample_age_seconds,
  COALESCE(p.has_gpu_fault, FALSE) AS has_gpu_fault,

  ROUND(100 * SAFE_DIVIDE(COALESCE(p.reporting_gpu_count, 0), NULLIF(COALESCE(p.expected_gpu_count, r.expected_gpu_count), 0)), 2)
    AS reporting_coverage_pct,
  ROUND(100 * SAFE_DIVIDE(COALESCE(p.reporting_gpu_count, 0) + COALESCE(p.stale_gpu_count, 0), NULLIF(COALESCE(p.expected_gpu_count, r.expected_gpu_count), 0)), 2)
    AS reporting_or_stale_coverage_pct,

  CASE
    WHEN COALESCE(p.expected_gpu_count, r.expected_gpu_count, 0) = 0 THEN 'Unknown'
    WHEN COALESCE(p.not_reporting_gpu_count, 0) > 0 THEN 'Not reporting'
    WHEN COALESCE(p.stale_gpu_count, 0) > 0 THEN 'Stale'
    WHEN COALESCE(p.reporting_gpu_count, 0) = COALESCE(p.expected_gpu_count, r.expected_gpu_count) THEN 'Reporting'
    ELSE 'Unknown'
  END AS machine_freshness_class,

  CASE
    WHEN COALESCE(p.expected_gpu_count, r.expected_gpu_count, 0) = 0 THEN 'no_expected_gpu_inventory'
    WHEN COALESCE(p.not_reporting_gpu_count, 0) > 0 THEN 'at_least_one_gpu_not_reporting_gt_10m'
    WHEN COALESCE(p.stale_gpu_count, 0) > 0 THEN 'at_least_one_gpu_stale_3_to_10m'
    WHEN COALESCE(p.reporting_gpu_count, 0) = COALESCE(p.expected_gpu_count, r.expected_gpu_count) THEN 'all_expected_gpus_reporting_under_3m'
    ELSE 'reconciliation_gap'
  END AS machine_freshness_reason,

  r.registry_source,
  r.inventory_last_seen_at,
  r.machine_last_heartbeat,
  CURRENT_TIMESTAMP() AS evaluated_at
FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v3` r
LEFT JOIN per_gpu p
  ON p.host = r.host;


-- 13) Fleet-level summary
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.fleet_reporting_summary_v3` AS
SELECT
  CURRENT_TIMESTAMP() AS as_of_timestamp,

  COUNT(*) AS registered_machine_count,
  COUNTIF(active) AS active_machine_count,
  COUNTIF(machine_freshness_class = 'Reporting') AS machines_reporting,
  COUNTIF(machine_freshness_class = 'Stale') AS machines_stale,
  COUNTIF(machine_freshness_class = 'Not reporting') AS machines_not_reporting,
  COUNTIF(machine_freshness_class = 'Unknown') AS machines_unknown,

  SUM(expected_gpu_count) AS expected_gpu_count,
  SUM(reporting_gpu_count) AS reporting_gpu_count,
  SUM(stale_gpu_count) AS stale_gpu_count,
  SUM(not_reporting_gpu_count) AS not_reporting_gpu_count,
  SUM(unknown_gpu_count) AS unknown_gpu_count,

  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS telemetry_reporting_coverage_pct,
  ROUND(100 * SAFE_DIVIDE(SUM(reporting_gpu_count + stale_gpu_count), NULLIF(SUM(expected_gpu_count), 0)), 2) AS telemetry_reporting_or_stale_coverage_pct,

  COUNTIF(has_gpu_fault) AS machines_with_gpu_fault,
  MAX(machine_sample_age_seconds) AS max_machine_sample_age_seconds
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`;


-- 14) Alert-ready views
-- 14a) Ingest stop (global)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_ingest_stop_v1` AS
WITH latest AS (
  SELECT MAX(sample_timestamp) AS global_last_sample_ts
  FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
)
SELECT
  CURRENT_TIMESTAMP() AS evaluated_at,
  global_last_sample_ts,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), global_last_sample_ts, SECOND) AS age_seconds,
  IF(global_last_sample_ts IS NULL OR TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), global_last_sample_ts, SECOND) > 180, TRUE, FALSE) AS alert_triggered,
  'global_ingest_stop_if_no_samples_for_over_180s' AS alert_rule
FROM latest;


-- 14b) Stale / Not reporting machines
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_stale_or_not_reporting_v1` AS
SELECT
  evaluated_at,
  host,
  machine_name,
  provider,
  plane,
  region,
  expected_gpu_count,
  reporting_gpu_count,
  stale_gpu_count,
  not_reporting_gpu_count,
  unknown_gpu_count,
  machine_freshness_class,
  machine_freshness_reason,
  machine_sample_age_seconds,
  has_gpu_fault
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_reporting_v3`
WHERE machine_freshness_class IN ('Stale', 'Not reporting');


-- 14c) Edge collector restart indicator
--      (multiple agent_instance_ids observed per host in the last 30 minutes)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_collector_restarts_v1` AS
WITH recent AS (
  SELECT
    LOWER(TRIM(host)) AS host,
    SAFE_CAST(sample_ts AS TIMESTAMP) AS sample_timestamp,
    REGEXP_EXTRACT(sampler_run_id, r'^edge-agent:([^:]+):') AS agent_instance_id
  FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1`
  WHERE SAFE_CAST(sample_ts AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE)
), agg AS (
  SELECT
    host,
    COUNT(*) AS samples_30m,
    COUNT(DISTINCT agent_instance_id) AS distinct_agent_instances_30m,
    ARRAY_AGG(DISTINCT agent_instance_id IGNORE NULLS ORDER BY agent_instance_id) AS agent_instances,
    MAX(sample_timestamp) AS last_sample_timestamp
  FROM recent
  GROUP BY host
)
SELECT
  CURRENT_TIMESTAMP() AS evaluated_at,
  host,
  samples_30m,
  distinct_agent_instances_30m,
  agent_instances,
  last_sample_timestamp,
  (distinct_agent_instances_30m > 1) AS alert_triggered,
  'edge_agent_instance_id_changed' AS alert_rule
FROM agg
WHERE distinct_agent_instances_30m > 1;


-- 14d) Sustained GPU faults
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_faults_sustained_v1` AS
WITH recent AS (
  SELECT
    host,
    COALESCE(gpu_key, CONCAT('idx:', CAST(COALESCE(gpu_index, -1) AS STRING))) AS gpu_identity,
    gpu_index,
    gpu_model,
    gpu_vendor,
    sample_timestamp,
    LOWER(COALESCE(gpu_status, '')) AS gpu_status
  FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
  WHERE sample_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
), agg AS (
  SELECT
    host,
    gpu_identity,
    ANY_VALUE(gpu_index) AS gpu_index,
    ANY_VALUE(gpu_model) AS gpu_model,
    ANY_VALUE(gpu_vendor) AS gpu_vendor,
    COUNT(*) AS samples_15m,
    COUNTIF(gpu_status = 'fault') AS fault_samples_15m,
    MIN(sample_timestamp) AS first_sample_ts,
    MAX(sample_timestamp) AS last_sample_ts,
    SAFE_DIVIDE(COUNTIF(gpu_status = 'fault'), COUNT(*)) AS fault_ratio
  FROM recent
  GROUP BY host, gpu_identity
)
SELECT
  CURRENT_TIMESTAMP() AS evaluated_at,
  host,
  gpu_identity,
  gpu_index,
  gpu_model,
  gpu_vendor,
  samples_15m,
  fault_samples_15m,
  ROUND(100 * fault_ratio, 2) AS fault_pct_15m,
  first_sample_ts,
  last_sample_ts,
  TRUE AS alert_triggered,
  'sustained_fault_ratio_ge_80pct_for_15m' AS alert_rule
FROM agg
WHERE samples_15m >= 5
  AND fault_ratio >= 0.8;


-- 14e) Coverage drop alert
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.alert_gpu_coverage_drop_v1` AS
SELECT
  as_of_timestamp AS evaluated_at,
  registered_machine_count,
  active_machine_count,
  expected_gpu_count,
  reporting_gpu_count,
  stale_gpu_count,
  not_reporting_gpu_count,
  unknown_gpu_count,
  telemetry_reporting_coverage_pct,
  telemetry_reporting_or_stale_coverage_pct,
  (
    telemetry_reporting_coverage_pct < 95
    OR telemetry_reporting_or_stale_coverage_pct < 99
  ) AS alert_triggered,
  'reporting_coverage_lt_95pct_or_reporting_plus_stale_lt_99pct' AS alert_rule
FROM `inbound-dahlia-507808-g1.fleet_ops.fleet_reporting_summary_v3`;


-- 15) Compatibility/backfill candidate for clean_ops.fact_gpu_telemetry_v1 consumers
--     This does NOT overwrite the existing fact table.
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.fact_gpu_telemetry_backfill_candidate_v1` AS
SELECT
  sample_timestamp AS ts_utc,
  provider,
  host AS machine_id,
  COALESCE(gpu_key, CONCAT(host, ':', CAST(COALESCE(gpu_index, -1) AS STRING))) AS gpu_id,
  gpu_vendor,
  gpu_model,
  gpu_status,
  gpu_utilization_pct AS util_gpu_pct,
  gpu_memory_used_mib AS mem_used_mib,
  gpu_memory_total_mib AS mem_total_mib,
  gpu_memory_utilization_pct AS mem_util_pct,
  temperature_celsius AS temp_c,
  power_watts AS power_w,
  host_reachable,
  vpn_online,
  collector_version,
  telemetry_backend,
  source_name,
  util_missing_reason,
  power_missing_reason,
  temperature_missing_reason,
  memory_used_missing_reason,
  memory_total_missing_reason
FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
WHERE sample_timestamp IS NOT NULL;

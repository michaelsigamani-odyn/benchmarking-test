-- =========================================================
-- GPU telemetry v2 model
-- - prodv2-only machine scope
-- - host-telemetry-service-only samples
-- - deduped raw sample stream
-- - intuitive view/table names (avoid biz_ops/tableau_* naming)
-- - rounded floating-point output formatting
--
-- Project is currently pinned to inbound-dahlia-507808-g1 to match
-- existing datasets in this repository.
-- =========================================================

-- 0) Dataset for operator-friendly, stable telemetry views
CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.fleet_ops`
OPTIONS (
  location = 'EU'
);

-- 1) Explicit prodv2 machine registry (authoritative include list)
CREATE TABLE IF NOT EXISTS `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v1` (
  host STRING NOT NULL,
  display_name STRING,
  site STRING,
  region STRING,
  environment STRING NOT NULL,
  active BOOL NOT NULL,
  notes STRING,
  PRIMARY KEY (host) NOT ENFORCED
);

-- Seed/refresh from existing edge registry for non-demo hosts.
-- Keep this merge so prodv2 scope remains explicit and auditable.
MERGE `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v1` T
USING (
  SELECT
    host,
    display_name,
    site,
    NULL AS region,
    'prodv2' AS environment,
    TRUE AS active,
    'Seeded from edge_machine_registry_v1 where is_demo=false. Review/override manually as needed.' AS notes
  FROM `inbound-dahlia-507808-g1.clean_ops.edge_machine_registry_v1`
  WHERE COALESCE(SAFE_CAST(is_demo AS BOOL), FALSE) = FALSE
) S
ON LOWER(TRIM(T.host)) = LOWER(TRIM(S.host))
WHEN MATCHED THEN
  UPDATE SET
    display_name = S.display_name,
    site = S.site,
    environment = S.environment,
    active = S.active,
    notes = S.notes
WHEN NOT MATCHED THEN
  INSERT (host, display_name, site, region, environment, active, notes)
  VALUES (S.host, S.display_name, S.site, S.region, S.environment, S.active, S.notes);

-- 2) Deduped raw sample stream (best-quality row per host+timestamp+gpu)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.raw_ops.machine_gpu_telemetry_samples_dedup_v2` AS
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
    ) AS quality_score
  FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1` s
),
ranked AS (
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

-- 3) Strict prodv2 host telemetry view
--    Only include rows produced by on-host telemetry service metadata.
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v2` AS
WITH prodv2_hosts AS (
  SELECT DISTINCT LOWER(TRIM(host)) AS host
  FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v1`
  WHERE active IS TRUE
),
typed AS (
  SELECT
    SAFE_CAST(sample_ts AS TIMESTAMP) AS sample_timestamp,
    LOWER(TRIM(host)) AS host,
    SAFE_CAST(gpu_index AS INT64) AS gpu_index,
    LOWER(TRIM(vendor)) AS gpu_vendor,
    gpu_name AS gpu_model,
    driver_version AS gpu_driver_version,
    gpu_status,
    ROUND(SAFE_CAST(util_gpu_pct AS FLOAT64), 2) AS gpu_utilization_pct,
    ROUND(SAFE_CAST(vram_pct AS FLOAT64), 2) AS vram_utilization_pct,
    ROUND(SAFE_CAST(power_w AS FLOAT64), 2) AS power_watts,
    ROUND(SAFE_CAST(temp_c AS FLOAT64), 2) AS temperature_celsius,
    ROUND(SAFE_CAST(load1 AS FLOAT64), 2) AS host_load_1m,
    ROUND(SAFE_CAST(mem_used_mib AS FLOAT64), 2) AS gpu_memory_used_mib,
    ROUND(SAFE_CAST(mem_total_mib AS FLOAT64), 2) AS gpu_memory_total_mib,
    SAFE_CAST(containers AS INT64) AS running_containers,
    SAFE_CAST(reachable AS BOOL) AS host_reachable,
    SAFE_CAST(vpn_online AS BOOL) AS vpn_online,
    site AS site_name,
    sampler_run_id AS collector_run_id,
    NULLIF(TRIM(ts_backend), '') AS telemetry_backend,
    NULLIF(TRIM(agent_version), '') AS telemetry_agent_version,
    CASE
      WHEN NULLIF(TRIM(agent_version), '') IS NOT NULL THEN TRUE
      WHEN REGEXP_CONTAINS(LOWER(COALESCE(ts_backend, '')), r'(host|telemetry|agent)') THEN TRUE
      ELSE FALSE
    END AS is_host_telemetry_service
  FROM `inbound-dahlia-507808-g1.raw_ops.machine_gpu_telemetry_samples_dedup_v2`
)
SELECT
  t.sample_timestamp,
  t.host,
  t.gpu_index,
  t.gpu_vendor,
  t.gpu_model,
  t.gpu_driver_version,
  t.gpu_status,
  t.gpu_utilization_pct,
  t.vram_utilization_pct,
  t.power_watts,
  t.temperature_celsius,
  t.host_load_1m,
  t.gpu_memory_used_mib,
  t.gpu_memory_total_mib,
  t.running_containers,
  t.host_reachable,
  t.vpn_online,
  t.site_name,
  t.collector_run_id,
  t.telemetry_backend,
  t.telemetry_agent_version,
  t.is_host_telemetry_service
FROM typed t
JOIN prodv2_hosts p
  ON t.host = p.host
WHERE t.sample_timestamp IS NOT NULL
  AND t.is_host_telemetry_service;

-- 4) Latest state per host+GPU
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_telemetry_latest_v2` AS
SELECT *
FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v2`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY host, COALESCE(gpu_index, -1)
  ORDER BY sample_timestamp DESC, collector_run_id DESC
) = 1;

-- 5) Host-level overview (intuitive naming + rounded metrics)
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.machine_telemetry_overview_v2` AS
WITH host_latest AS (
  SELECT
    host,
    MAX(sample_timestamp) AS last_sample_timestamp,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(sample_timestamp), SECOND) AS sample_age_seconds,
    COUNT(*) AS reporting_gpu_count,
    MAX(IF(LOWER(COALESCE(gpu_status, '')) = 'fault', 1, 0)) > 0 AS has_gpu_fault,
    ROUND(MAX(gpu_utilization_pct), 2) AS gpu_utilization_peak_pct,
    ROUND(SUM(power_watts), 2) AS total_power_watts,
    ROUND(MAX(temperature_celsius), 2) AS max_temperature_celsius,
    MAX(running_containers) AS running_containers,
    ROUND(MAX(host_load_1m), 2) AS host_load_1m,
    LOGICAL_OR(host_reachable IS TRUE) AS any_host_reachable,
    LOGICAL_OR(vpn_online IS TRUE) AS any_vpn_online
  FROM `inbound-dahlia-507808-g1.fleet_ops.machine_gpu_telemetry_latest_v2`
  GROUP BY host
)
SELECT
  r.host,
  COALESCE(r.display_name, r.host) AS machine_name,
  r.site,
  r.region,
  r.environment,
  r.active AS registry_active,
  h.last_sample_timestamp,
  h.sample_age_seconds,
  CASE
    WHEN h.last_sample_timestamp IS NULL THEN 'NO_TELEMETRY'
    WHEN h.sample_age_seconds <= 120 THEN 'FRESH'
    WHEN h.sample_age_seconds <= 600 THEN 'STALE'
    ELSE 'OLD'
  END AS telemetry_status,
  h.reporting_gpu_count,
  h.has_gpu_fault,
  h.gpu_utilization_peak_pct,
  h.total_power_watts,
  h.max_temperature_celsius,
  h.running_containers,
  h.host_load_1m,
  h.any_host_reachable,
  h.any_vpn_online
FROM `inbound-dahlia-507808-g1.clean_ops.prodv2_machine_registry_v1` r
LEFT JOIN host_latest h
  ON LOWER(TRIM(r.host)) = h.host
WHERE r.active IS TRUE;

-- 6) Fleet summary
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.fleet_ops.fleet_telemetry_summary_v2` AS
SELECT
  CURRENT_TIMESTAMP() AS as_of_timestamp,
  COUNT(*) AS registered_host_count,
  COUNTIF(last_sample_timestamp IS NOT NULL) AS hosts_with_telemetry,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(last_sample_timestamp IS NOT NULL), COUNT(*)), 2) AS telemetry_coverage_pct,
  COUNTIF(telemetry_status = 'FRESH') AS hosts_fresh,
  COUNTIF(has_gpu_fault) AS hosts_with_gpu_fault,
  ROUND(AVG(gpu_utilization_peak_pct), 2) AS average_gpu_utilization_pct,
  ROUND(AVG(total_power_watts), 2) AS average_power_watts
FROM `inbound-dahlia-507808-g1.fleet_ops.machine_telemetry_overview_v2`;

-- BigQuery post-load duplicate checks.
--
-- Run with:
--   bq query --nouse_legacy_sql < scripts/db/bq_dedup_checks.sql
--
-- If any assertion fails, the script exits non-zero.

DECLARE duplicate_groups INT64;
DECLARE has_view BOOL;

-- =========================================================
-- 1) raw_ops.workload_conditions_raw_v1
--    expected unique key: (provider, provider_run_id, payload_sha256)
-- =========================================================
SET duplicate_groups = (
  SELECT COUNT(*)
  FROM (
    SELECT provider, provider_run_id, payload_sha256
    FROM `inbound-dahlia-507808-g1.raw_ops.workload_conditions_raw_v1`
    GROUP BY provider, provider_run_id, payload_sha256
    HAVING COUNT(*) > 1
  )
);
ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in raw_ops.workload_conditions_raw_v1';

-- =========================================================
-- 2) clean_ops.workload_conditions_v1
--    expected unique key: (provider, workload_id, workload_type, as_of_ts)
-- =========================================================
SET duplicate_groups = (
  SELECT COUNT(*)
  FROM (
    SELECT provider, workload_id, workload_type, as_of_ts
    FROM `inbound-dahlia-507808-g1.clean_ops.workload_conditions_v1`
    GROUP BY provider, workload_id, workload_type, as_of_ts
    HAVING COUNT(*) > 1
  )
);
ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in clean_ops.workload_conditions_v1';

-- =========================================================
-- 3) clean_ops.workload_timing_v1
--    expected unique key: (provider, workload_id, workload_type, as_of_ts)
-- =========================================================
SET duplicate_groups = (
  SELECT COUNT(*)
  FROM (
    SELECT provider, workload_id, workload_type, as_of_ts
    FROM `inbound-dahlia-507808-g1.clean_ops.workload_timing_v1`
    GROUP BY provider, workload_id, workload_type, as_of_ts
    HAVING COUNT(*) > 1
  )
);
ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in clean_ops.workload_timing_v1';

-- =========================================================
-- 4) raw_ops.edge_gpu_samples_v1
--    expected natural key: (host, sample_ts, gpu_index, vendor)
-- =========================================================
SET duplicate_groups = (
  SELECT COUNT(*)
  FROM (
    SELECT
      COALESCE(LOWER(TRIM(host)), '_unknown_host_') AS host,
      SAFE_CAST(sample_ts AS TIMESTAMP) AS sample_ts,
      COALESCE(SAFE_CAST(gpu_index AS INT64), -1) AS gpu_index,
      COALESCE(LOWER(TRIM(vendor)), '_unknown_vendor_') AS vendor
    FROM `inbound-dahlia-507808-g1.raw_ops.edge_gpu_samples_v1`
    GROUP BY 1, 2, 3, 4
    HAVING COUNT(*) > 1
  )
);
ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in raw_ops.edge_gpu_samples_v1';

-- =========================================================
-- 5) clean_ops.machine_gpu_telemetry_prodv2_v2
--    expected unique key: (host, sample_timestamp, gpu_index)
-- =========================================================
SET has_view = EXISTS (
  SELECT 1
  FROM `inbound-dahlia-507808-g1.clean_ops.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = 'machine_gpu_telemetry_prodv2_v2'
);

IF has_view THEN
  SET duplicate_groups = (
    SELECT COUNT(*)
    FROM (
      SELECT host, sample_timestamp, COALESCE(gpu_index, -1) AS gpu_index
      FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v2`
      GROUP BY host, sample_timestamp, gpu_index
      HAVING COUNT(*) > 1
    )
  );
  ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in clean_ops.machine_gpu_telemetry_prodv2_v2';
END IF;

-- =========================================================
-- 6) clean_ops.machine_gpu_telemetry_prodv2_v3
--    expected unique key: (host, sample_timestamp, gpu_identity)
-- =========================================================
SET has_view = EXISTS (
  SELECT 1
  FROM `inbound-dahlia-507808-g1.clean_ops.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = 'machine_gpu_telemetry_prodv2_v3'
);

IF has_view THEN
  SET duplicate_groups = (
    SELECT COUNT(*)
    FROM (
      SELECT
        host,
        sample_timestamp,
        COALESCE(gpu_key, CONCAT('idx:', CAST(COALESCE(gpu_index, -1) AS STRING))) AS gpu_identity
      FROM `inbound-dahlia-507808-g1.clean_ops.machine_gpu_telemetry_prodv2_v3`
      GROUP BY host, sample_timestamp, gpu_identity
      HAVING COUNT(*) > 1
    )
  );
  ASSERT duplicate_groups = 0 AS 'Duplicate key groups found in clean_ops.machine_gpu_telemetry_prodv2_v3';
END IF;

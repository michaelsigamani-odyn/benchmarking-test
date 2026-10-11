-- Consolidated v1.1 DDL (first-run safe)
-- Replace:
-- - PROJECT
-- - EU_KMS_KEY
-- - optional location (EU vs europe-west2 for UK residency)
-- =========================================================
-- 0) DATASETS (choose location deliberately)
-- =========================================================
CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.raw_ops`
OPTIONS (
  location = 'EU' -- or 'europe-west2' if UK residency required
);

CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.clean_ops`
OPTIONS (
  location = 'EU'
);

CREATE SCHEMA IF NOT EXISTS `inbound-dahlia-507808-g1.biz_ops`
OPTIONS (
  location = 'EU'
);

-- =========================================================
-- 1) RAW REDACTED OBSERVATIONS (append)
--    observation-addressed ID (preferred): stable per observation
-- =========================================================
CREATE TABLE IF NOT EXISTS `inbound-dahlia-507808-g1.raw_ops.workload_conditions_raw_v1` (
  raw_record_id STRING NOT NULL,                     -- hash(provider, provider_run_id, payload_sha256, ingest_run_id)
  ingest_run_id STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  event_at TIMESTAMP,
  event_date DATE NOT NULL,                          -- ETL: COALESCE(DATE(event_at), DATE(fetched_at))

  source_system STRING NOT NULL,
  provider STRING NOT NULL,
  workload_type STRING,                              -- finetune | serving
  workload_id STRING,
  provider_run_id STRING NOT NULL,

  -- classification (fail closed in collector)
  is_benchmark_run BOOL NOT NULL,
  is_customer_workload BOOL NOT NULL,                -- unknown => TRUE in collector

  -- pseudonyms only (no raw identifiers)
  user_hmac STRING,
  owner_hmac STRING,
  user_hmac_key_version STRING,                      -- key version used
  owner_hmac_key_version STRING,

  -- redaction metadata
  redaction_version STRING NOT NULL,
  redaction_applied BOOL NOT NULL,
  redaction_scan_passed BOOL NOT NULL,               -- must be TRUE for successful batch
  redaction_scan_findings ARRAY<STRING>,             -- optional matched patterns (non-secret descriptors)

  -- canonical hash over canonicalized REDACTED payload
  payload_sha256 STRING NOT NULL,

  payload_redacted JSON NOT NULL,

  PRIMARY KEY (raw_record_id) NOT ENFORCED
)
PARTITION BY event_date
CLUSTER BY provider, source_system, provider_run_id;

-- latest-per-content dedupe helper
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.raw_ops.workload_conditions_raw_dedup_v1` AS
SELECT *
FROM `inbound-dahlia-507808-g1.raw_ops.workload_conditions_raw_v1`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY provider, provider_run_id, payload_sha256
  ORDER BY fetched_at DESC, raw_record_id DESC
) = 1;

-- =========================================================
-- 2) CLEAN CONDITIONS (v1 minimal + flags + provenance)
-- =========================================================
CREATE TABLE IF NOT EXISTS `inbound-dahlia-507808-g1.clean_ops.workload_conditions_v1` (
  as_of_ts TIMESTAMP NOT NULL,
  provider STRING NOT NULL,
  workload_id STRING NOT NULL,
  workload_type STRING NOT NULL,
  provider_run_id STRING,

  is_benchmark_run BOOL NOT NULL,
  is_customer_workload BOOL NOT NULL,

  model_id STRING,
  model_id_f INT64,
  model_id_source STRING,
  model_id_reason STRING,

  training_objective STRING,
  training_objective_f INT64,
  training_objective_source STRING,
  training_objective_reason STRING,

  training_method STRING,
  training_method_f INT64,
  training_method_source STRING,
  training_method_reason STRING,

  lora_rank INT64,
  lora_rank_f INT64,
  lora_rank_source STRING,
  lora_rank_reason STRING,

  lora_alpha INT64,
  lora_alpha_f INT64,
  lora_alpha_source STRING,
  lora_alpha_reason STRING,

  batch_size_value INT64,                            -- nullable for "max"/auto
  batch_size_raw STRING,                             -- e.g. "max"
  batch_size_kind STRING,                            -- per_device|effective|provider_auto|unknown
  batch_size_f INT64,
  batch_size_source STRING,
  batch_size_reason STRING,

  learning_rate FLOAT64,
  learning_rate_f INT64,
  learning_rate_source STRING,
  learning_rate_reason STRING,

  seq_len INT64,
  seq_len_f INT64,
  seq_len_source STRING,
  seq_len_reason STRING,

  gpu_count INT64,
  gpu_count_f INT64,
  gpu_count_source STRING,
  gpu_count_reason STRING,

  precision STRING,
  precision_f INT64,
  precision_source STRING,
  precision_reason STRING,

  -- sanitized URI; for customer rows collector should null or heavily mask
  dataset_uri_sanitized STRING,
  dataset_uri_sanitized_f INT64,
  dataset_uri_sanitized_source STRING,
  dataset_uri_sanitized_reason STRING,

  -- benchmark reproducibility path (non-customer): content hash
  dataset_content_hash STRING,                       -- hash of dataset bytes/content manifest
  dataset_content_hash_f INT64,
  dataset_content_hash_source STRING,
  dataset_content_hash_reason STRING,

  -- customer privacy path: pseudonymous dataset identity
  dataset_identity_hmac STRING,
  dataset_identity_hmac_f INT64,
  dataset_identity_hmac_source STRING,
  dataset_identity_hmac_reason STRING,
  dataset_identity_hmac_key_version STRING,

  tokenizer_id STRING,
  tokenizer_id_f INT64,
  tokenizer_id_source STRING,
  tokenizer_id_reason STRING,

  tokenizer_fallback_used BOOL,
  tokenizer_fallback_used_f INT64,
  tokenizer_fallback_reason STRING,

  source_system STRING NOT NULL,
  source_record_ref STRING,                          -- raw_record_id
  ingest_run_id STRING NOT NULL,

  PRIMARY KEY (provider, workload_id, workload_type, as_of_ts) NOT ENFORCED
)
PARTITION BY DATE(as_of_ts)
CLUSTER BY provider, workload_type, workload_id;

-- =========================================================
-- 3) CLEAN TIMING (v1 = wall + training only)
-- =========================================================
CREATE TABLE IF NOT EXISTS `inbound-dahlia-507808-g1.clean_ops.workload_timing_v1` (
  as_of_ts TIMESTAMP NOT NULL,
  provider STRING NOT NULL,
  workload_id STRING NOT NULL,
  workload_type STRING NOT NULL,

  submitted_at TIMESTAMP,
  submitted_at_f INT64,
  submitted_at_source STRING,                        -- client_clock|provider_server_clock|inferred
  submitted_at_reason STRING,

  model_available_at TIMESTAMP,
  model_available_at_f INT64,                        -- inferred proxy => 0
  model_available_at_source STRING,
  model_available_at_reason STRING,

  trainer_started_at TIMESTAMP,
  trainer_started_at_f INT64,
  trainer_started_at_source STRING,
  trainer_started_at_reason STRING,

  training_ended_at TIMESTAMP,
  training_ended_at_f INT64,
  training_ended_at_source STRING,
  training_ended_at_reason STRING,

  wall_time_min FLOAT64,
  wall_time_min_f INT64,
  wall_time_min_source STRING,
  wall_time_min_reason STRING,

  training_time_min FLOAT64,
  training_time_min_f INT64,
  training_time_min_source STRING,
  training_time_min_reason STRING,

  benchmark_timing_eligible BOOL,
  benchmark_timing_eligible_reason STRING,

  source_system STRING NOT NULL,
  ingest_run_id STRING NOT NULL,

  PRIMARY KEY (provider, workload_id, workload_type, as_of_ts) NOT ENFORCED
)
PARTITION BY DATE(as_of_ts)
CLUSTER BY provider, workload_type, workload_id;

-- =========================================================
-- 4) LATEST VIEWS (no fanout in flat join)
-- =========================================================
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.workload_conditions_latest_v1` AS
SELECT *
FROM `inbound-dahlia-507808-g1.clean_ops.workload_conditions_v1`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY provider, workload_id, workload_type
  ORDER BY as_of_ts DESC
) = 1;

CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.clean_ops.workload_timing_latest_v1` AS
SELECT *
FROM `inbound-dahlia-507808-g1.clean_ops.workload_timing_v1`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY provider, workload_id, workload_type
  ORDER BY as_of_ts DESC
) = 1;

-- =========================================================
-- 5) STAKEHOLDER VIEW (benchmark-only, customer-excluded)
-- =========================================================
CREATE OR REPLACE VIEW `inbound-dahlia-507808-g1.biz_ops.workload_benchmark_flat_v1` AS
SELECT
  c.as_of_ts,
  c.provider, c.workload_id, c.workload_type, c.provider_run_id,
  c.is_benchmark_run, c.is_customer_workload,

  c.model_id, c.model_id_f,
  c.training_objective, c.training_objective_f,
  c.training_method, c.training_method_f,
  c.lora_rank, c.lora_rank_f,
  c.lora_alpha, c.lora_alpha_f,
  c.batch_size_value, c.batch_size_raw, c.batch_size_kind, c.batch_size_f,
  c.learning_rate, c.learning_rate_f,
  c.seq_len, c.seq_len_f,
  c.gpu_count, c.gpu_count_f,
  c.precision, c.precision_f,
  c.dataset_uri_sanitized, c.dataset_uri_sanitized_f,
  c.dataset_content_hash, c.dataset_content_hash_f,
  c.tokenizer_id, c.tokenizer_id_f,
  c.tokenizer_fallback_used, c.tokenizer_fallback_used_f,

  t.submitted_at, t.submitted_at_f, t.submitted_at_source,
  t.model_available_at, t.model_available_at_f, t.model_available_at_source,
  t.trainer_started_at, t.trainer_started_at_f,
  t.training_ended_at, t.training_ended_at_f,
  t.wall_time_min, t.wall_time_min_f,
  t.training_time_min, t.training_time_min_f,
  t.benchmark_timing_eligible, t.benchmark_timing_eligible_reason,

  -- lineage back for traceability
  c.source_system AS conditions_source_system,
  c.ingest_run_id AS conditions_ingest_run_id,
  c.source_record_ref AS conditions_source_record_ref,
  t.source_system AS timing_source_system,
  t.ingest_run_id AS timing_ingest_run_id
FROM `inbound-dahlia-507808-g1.clean_ops.workload_conditions_latest_v1` c
LEFT JOIN `inbound-dahlia-507808-g1.clean_ops.workload_timing_latest_v1` t
USING (provider, workload_id, workload_type)
WHERE c.is_benchmark_run AND NOT c.is_customer_workload;

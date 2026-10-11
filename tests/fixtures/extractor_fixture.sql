-- Synthetic extractor fixture data for local-only validation.
-- Uses real Postgres types (UUID, NUMERIC, TIMESTAMPTZ, JSONB, BIGINT, nullable/unicode text).

DROP VIEW IF EXISTS public.ingest_job_placement_v1;
DROP TABLE IF EXISTS public.ingest_job_placement_fixture_src;

CREATE TABLE public.ingest_job_placement_fixture_src (
  job_id uuid PRIMARY KEY,
  gpu_identifiers jsonb,
  node_ids jsonb,
  gpu_reservation_id text,
  gpu_model_class text,
  min_gpu_vram_gb integer,
  num_workers integer,
  price_book_hourly_rate_usd numeric(20,10),
  lifecycle_attempt integer,
  created_at timestamptz,
  observed_at timestamptz,
  error_message text,
  error_summary text,
  failure_reason text,
  accepted_recommendation_json jsonb,
  response_json jsonb,
  num_input_tokens_seen bigint,
  dataset_train_token_count bigint,
  context_length_tokens integer,
  nullable_note text,
  unicode_note text,
  not_granted_internal_note text
);

INSERT INTO public.ingest_job_placement_fixture_src (
  job_id,
  gpu_identifiers,
  node_ids,
  gpu_reservation_id,
  gpu_model_class,
  min_gpu_vram_gb,
  num_workers,
  price_book_hourly_rate_usd,
  lifecycle_attempt,
  created_at,
  observed_at,
  error_message,
  error_summary,
  failure_reason,
  accepted_recommendation_json,
  response_json,
  num_input_tokens_seen,
  dataset_train_token_count,
  context_length_tokens,
  nullable_note,
  unicode_note,
  not_granted_internal_note
)
VALUES
(
  '550e8400-e29b-41d4-a716-446655440000'::uuid,
  '["GPU-123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174001"]'::jsonb,
  '["node-a"]'::jsonb,
  ' https://service.example/path?X-Amz-Signature=abc&X-Amz-Credential=def#frag ',
  'a100',
  80,
  2,
  1.2500000000,
  3,
  '2026-10-11 05:10:00.123456+00',
  '2026-10-11 05:10:00.654321+00',
  'FAKEFAKEFAKE hf_FAKE @example.invalid 10.1.2.3 ip-10-1-2-3.ec2.internal arn:aws:iam::000000000000 BEGIN PRIVATE KEY X-Amz-Signature X-Amz-Credential CUSTOMER SECRET other-supplier 10.9.9.9 supplier-host-1',
  'context with signed url https://download.example/path?X-Amz-Signature=aaa&X-Amz-Credential=bbb',
  'bearer hf_FAKE',
  '{"candidate_id":"c1","machine_id":"m1","provider":"gcp","rank":1,"reservation_expires_at":"2026-10-11T05:00:00Z","reservation_id":"r1","source":"fixture","selected_placement":{"node_id":"node-1","gpu_ids":["GPU-123e4567-e89b-12d3-a456-426614174000","123e4567-e89b-12d3-a456-426614174001"]},"pricing":{"cost_per_hour_usd":1.25},"specs":{"gpu":"H100"}}'::jsonb,
  '{"status":"ok","resource_id":"res-1","next_route":"route-1"}'::jsonb,
  9007199254740993,
  9223372036854775000,
  8192,
  NULL,
  '🧪 café – 東京',
  'must-not-be-selectable'
);

CREATE OR REPLACE VIEW public.ingest_job_placement_v1 AS
SELECT
  job_id,
  gpu_identifiers,
  node_ids,
  gpu_reservation_id,
  gpu_model_class,
  min_gpu_vram_gb,
  num_workers,
  price_book_hourly_rate_usd,
  lifecycle_attempt
FROM public.ingest_job_placement_fixture_src;

-- Assertions (14) for local embedded Postgres fixture:
-- 1) numeric values serialize as exact strings; captured_at is UTC RFC3339 with microseconds.
-- 2) scanner matches values only, never column names (token-ish columns are allowed).
-- 3) structured-field poison aborts the run.
-- 4) findings contain only metadata fields (table,row_pk,field,pattern) and no matched secret text.
-- 5) startup enforces config==grants + has_column_privilege; role can SELECT * on the view but cannot read non-granted source column.
-- 6) URL sanitization is applied before HMAC; id values are trim+lower before HMAC; empty string remains empty string.
-- 7) one read-only REPEATABLE READ transaction; in-tx count must equal fetched rows; row limit hit aborts.
-- 8) gpu_identifiers/node_ids shape filtering and sanitisation-only behavior.
-- 9) row_json contains only real view columns.
-- 10) change-only re-run with no source changes emits zero rows.
-- 11) mutation run emits exactly: 1 changed row, 1 tombstone, 1 new row.
-- 12) sink layout is correct and _manifest.json is last; loader-side manifest validation fails if a listed file is missing.
-- 13) same-run-id overwrite fails (if_generation_match=0 semantics), and 4KB truncation helper includes marker.
-- 14) no poison values appear in any output file or stdout/stderr.

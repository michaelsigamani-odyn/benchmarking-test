-- Local synthetic fixture with all 14 granted objects.
-- Realism: id / owner_user_id / user_id are TEXT (not UUID).

DROP VIEW IF EXISTS public.ingest_job_placement_v1;

DROP TABLE IF EXISTS public.container_gpu_assignments;
DROP TABLE IF EXISTS public.ray_cluster_workers;
DROP TABLE IF EXISTS public.ray_clusters;
DROP TABLE IF EXISTS public.gpu_inventory;
DROP TABLE IF EXISTS public.nodes;
DROP TABLE IF EXISTS public.gpu_baseline_rates;
DROP TABLE IF EXISTS public.gpu_reservations;
DROP TABLE IF EXISTS public.finetune_metrics_history;
DROP TABLE IF EXISTS public.job_cost_summary;
DROP TABLE IF EXISTS public.finetune_billing_intervals;
DROP TABLE IF EXISTS public.scheduler_workload_requests;
DROP TABLE IF EXISTS public.post_training_workloads;
DROP TABLE IF EXISTS public.ray_train_jobs;
DROP TABLE IF EXISTS public.ingest_job_placement_fixture_src;

CREATE TABLE public.ray_train_jobs (
  id text PRIMARY KEY,
  owner_user_id text,
  dataset_s3_key text,
  status text,
  error_message text
);

CREATE TABLE public.post_training_workloads (
  id text PRIMARY KEY,
  owner_user_id text,
  status text
);

CREATE TABLE public.scheduler_workload_requests (
  id text PRIMARY KEY,
  user_id text,
  accepted_recommendation_json jsonb,
  response_json jsonb,
  status text
);

CREATE TABLE public.finetune_billing_intervals (
  id text PRIMARY KEY,
  owner_user_id text,
  amount_usd numeric(20,10)
);

CREATE TABLE public.job_cost_summary (
  job_id text PRIMARY KEY,
  tenant_id text,
  total_cost_usd numeric(20,10)
);

CREATE TABLE public.finetune_metrics_history (
  id text PRIMARY KEY,
  metric_name text,
  metric_value numeric(20,10)
);

CREATE TABLE public.gpu_reservations (
  id text PRIMARY KEY,
  user_id text,
  reservation_state text
);

CREATE TABLE public.gpu_baseline_rates (
  provider text,
  sku text,
  intake_type text,
  usd_per_hour numeric(20,10),
  PRIMARY KEY (provider, sku, intake_type)
);

CREATE TABLE public.nodes (
  id text PRIMARY KEY,
  provider text
);

CREATE TABLE public.gpu_inventory (
  gpu_key text PRIMARY KEY,
  node_id text,
  gpu_model_class text
);

CREATE TABLE public.ray_clusters (
  id text PRIMARY KEY,
  user_id text,
  status text
);

CREATE TABLE public.ray_cluster_workers (
  id text PRIMARY KEY,
  cluster_id text,
  node_id text
);

CREATE TABLE public.container_gpu_assignments (
  container_id text,
  gpu_key text,
  assigned_at timestamptz,
  PRIMARY KEY (container_id, gpu_key)
);

CREATE TABLE public.ingest_job_placement_fixture_src (
  row_id text PRIMARY KEY,
  job_id text,
  gpu_identifiers jsonb,
  node_ids jsonb,
  gpu_reservation_id text,
  gpu_model_class text,
  min_gpu_vram_gb integer,
  num_workers integer,
  price_book_hourly_rate_usd numeric(20,10),
  lifecycle_attempt integer,
  error_message text,
  not_granted_internal_note text
);

-- hashed columns: owner_user_id + dataset_s3_key -> include normal, empty, whitespace, null
INSERT INTO public.ray_train_jobs VALUES
('rtj-normal', 'owner-normal', 's3://bucket/train.jsonl', 'ok', 'contact me at user@example.com'),
('rtj-empty',  '',            '',                    'ok', 'clean text'),
('rtj-space',  '   ',         '   ',                 'ok', 'clean text'),
('rtj-null',   NULL,          NULL,                  'ok', 'clean text');

INSERT INTO public.post_training_workloads VALUES
('ptw-normal', 'owner-normal', 'ready'),
('ptw-empty',  '',             'ready'),
('ptw-space',  '   ',          'ready'),
('ptw-null',   NULL,           'ready');

INSERT INTO public.scheduler_workload_requests VALUES
('swr-normal', 'user-normal',
 '{"candidate_id":"c1","selected_placement":{"node_id":"node-1","gpu_ids":["GPU-123e4567-e89b-12d3-a456-426614174000","123e4567-e89b-12d3-a456-426614174001"]},"pricing":{"cost_per_hour_usd":1.25},"specs":{"gpu":"H100"}}',
 '{"status":"ok","resource_id":"r1","next_route":"queue-a"}',
 'ok'),
('swr-empty', '',
 '{"candidate_id":"c2","selected_placement":{"node_id":"node-2","gpu_ids":["GPU-123"]},"pricing":{"cost_per_hour_usd":2.25}}',
 '{"status":"ok"}',
 'ok'),
('swr-space', '   ',
 '{"candidate_id":"c3","selected_placement":{"node_id":"node-3","gpu_ids":["GPU-124"]}}',
 '{"status":"ok"}',
 'ok'),
('swr-null', NULL,
 '{"candidate_id":"c4","selected_placement":{"node_id":"node-4","gpu_ids":["GPU-125"]}}',
 '{"status":"ok"}',
 'ok');

INSERT INTO public.finetune_billing_intervals VALUES
('fbi-normal','owner-normal',12.5000000000),
('fbi-empty','',13.5000000000),
('fbi-space','   ',14.5000000000),
('fbi-null',NULL,15.5000000000);

INSERT INTO public.job_cost_summary VALUES
('jcs-normal','tenant-1',20.2500000000),
('jcs-empty','',21.2500000000),
('jcs-space','   ',22.2500000000),
('jcs-null',NULL,23.2500000000);

INSERT INTO public.finetune_metrics_history VALUES
('fmh-1','loss',0.1234000000);

INSERT INTO public.gpu_reservations VALUES
('gr-normal','user-normal','active'),
('gr-empty','',           'active'),
('gr-space','   ',        'active'),
('gr-null',NULL,          'active');

INSERT INTO public.gpu_baseline_rates VALUES
('gcp','h100','on_demand',4.5000000000);

INSERT INTO public.nodes VALUES
('node-a','gcp');

INSERT INTO public.gpu_inventory VALUES
('gpu-key-1','node-a','h100');

INSERT INTO public.ray_clusters VALUES
('rc-normal','user-normal','running'),
('rc-empty','',           'running'),
('rc-space','   ',        'running'),
('rc-null',NULL,          'running');

INSERT INTO public.ray_cluster_workers VALUES
('rcw-1','rc-normal','node-a');

INSERT INTO public.container_gpu_assignments VALUES
('container-1','gpu-key-1','2026-10-11 05:10:00+00');

-- hashed columns: job_id + gpu_reservation_id -> include normal, empty, whitespace, null
INSERT INTO public.ingest_job_placement_fixture_src VALUES
(
 'ijp-normal',
 'job-normal',
 '["GPU-123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174001"]'::jsonb,
 '["node-a"]'::jsonb,
 ' https://service.example/path?X-Amz-Signature=abc&X-Amz-Credential=def#frag ',
 'a100',
 80,
 2,
 1.2500000000,
 3,
 'signed url https://s-host.example/path?X-Amz-Signature=abc&X-Amz-Credential=def and prose ? mark',
 'must-not-be-selectable'
),
(
 'ijp-empty',
 '',
 '["GPU-9"]'::jsonb,
 '["node-e"]'::jsonb,
 '',
 'a100',
 80,
 1,
 1.0000000000,
 1,
 'ok',
 'must-not-be-selectable'
),
(
 'ijp-space',
 '   ',
 '["GPU-10"]'::jsonb,
 '["node-s"]'::jsonb,
 '   ',
 'a100',
 80,
 1,
 1.0000000000,
 1,
 'ok',
 'must-not-be-selectable'
),
(
 'ijp-null',
 NULL,
 '["GPU-11"]'::jsonb,
 '["node-n"]'::jsonb,
 NULL,
 'a100',
 80,
 1,
 1.0000000000,
 1,
 'ok',
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

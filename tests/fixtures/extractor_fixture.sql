-- Local synthetic fixture with all 14 granted objects.

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
  id uuid PRIMARY KEY,
  owner_user_id uuid,
  dataset_s3_key text,
  status text,
  error_message text
);

CREATE TABLE public.post_training_workloads (
  id uuid PRIMARY KEY,
  owner_user_id uuid,
  status text
);

CREATE TABLE public.scheduler_workload_requests (
  id uuid PRIMARY KEY,
  user_id uuid,
  accepted_recommendation_json jsonb,
  response_json jsonb,
  status text
);

CREATE TABLE public.finetune_billing_intervals (
  id uuid PRIMARY KEY,
  owner_user_id uuid,
  amount_usd numeric(20,10)
);

CREATE TABLE public.job_cost_summary (
  job_id uuid PRIMARY KEY,
  tenant_id text,
  total_cost_usd numeric(20,10)
);

CREATE TABLE public.finetune_metrics_history (
  id uuid PRIMARY KEY,
  metric_name text,
  metric_value numeric(20,10)
);

CREATE TABLE public.gpu_reservations (
  id uuid PRIMARY KEY,
  user_id uuid,
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
  id uuid PRIMARY KEY,
  user_id uuid,
  status text
);

CREATE TABLE public.ray_cluster_workers (
  id uuid PRIMARY KEY,
  cluster_id uuid,
  node_id text
);

CREATE TABLE public.container_gpu_assignments (
  container_id text,
  gpu_key text,
  assigned_at timestamptz,
  PRIMARY KEY (container_id, gpu_key)
);

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
  error_message text,
  not_granted_internal_note text
);

INSERT INTO public.ray_train_jobs VALUES
('11111111-1111-1111-1111-111111111111','aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','s3://bucket/train.jsonl','ok','contact me at user@example.com');

INSERT INTO public.post_training_workloads VALUES
('22222222-2222-2222-2222-222222222222','bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb','ready');

INSERT INTO public.scheduler_workload_requests VALUES
('33333333-3333-3333-3333-333333333333','cccccccc-cccc-cccc-cccc-cccccccccccc',
 '{"candidate_id":"c1","selected_placement":{"node_id":"node-1","gpu_ids":["GPU-123e4567-e89b-12d3-a456-426614174000","123e4567-e89b-12d3-a456-426614174001"]},"pricing":{"cost_per_hour_usd":1.25},"specs":{"gpu":"H100"}}',
 '{"status":"ok","resource_id":"r1","next_route":"queue-a"}',
 'ok');

INSERT INTO public.finetune_billing_intervals VALUES
('44444444-4444-4444-4444-444444444444','dddddddd-dddd-dddd-dddd-dddddddddddd',12.5000000000);

INSERT INTO public.job_cost_summary VALUES
('55555555-5555-5555-5555-555555555555','tenant-1',20.2500000000);

INSERT INTO public.finetune_metrics_history VALUES
('66666666-6666-6666-6666-666666666666','loss',0.1234000000);

INSERT INTO public.gpu_reservations VALUES
('77777777-7777-7777-7777-777777777777','eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee','active');

INSERT INTO public.gpu_baseline_rates VALUES
('gcp','h100','on_demand',4.5000000000);

INSERT INTO public.nodes VALUES
('node-a','gcp');

INSERT INTO public.gpu_inventory VALUES
('gpu-key-1','node-a','h100');

INSERT INTO public.ray_clusters VALUES
('88888888-8888-8888-8888-888888888888','ffffffff-ffff-ffff-ffff-ffffffffffff','running');

INSERT INTO public.ray_cluster_workers VALUES
('99999999-9999-9999-9999-999999999999','88888888-8888-8888-8888-888888888888','node-a');

INSERT INTO public.container_gpu_assignments VALUES
('container-1','gpu-key-1','2026-10-11 05:10:00+00');

INSERT INTO public.ingest_job_placement_fixture_src VALUES
(
 '550e8400-e29b-41d4-a716-446655440000',
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

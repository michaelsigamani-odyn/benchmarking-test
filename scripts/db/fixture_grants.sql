-- Fixture grants for local tests only.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odyn_ingest_ro') THEN
    CREATE ROLE odyn_ingest_ro NOLOGIN;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO odyn_ingest_ro;

GRANT SELECT (id, owner_user_id, dataset_s3_key, status, error_message) ON public.ray_train_jobs TO odyn_ingest_ro;
GRANT SELECT (id, owner_user_id, status) ON public.post_training_workloads TO odyn_ingest_ro;
GRANT SELECT (id, user_id, accepted_recommendation_json, response_json, status) ON public.scheduler_workload_requests TO odyn_ingest_ro;
GRANT SELECT (id, owner_user_id, amount_usd) ON public.finetune_billing_intervals TO odyn_ingest_ro;
GRANT SELECT (job_id, tenant_id, total_cost_usd) ON public.job_cost_summary TO odyn_ingest_ro;
GRANT SELECT (id, metric_name, metric_value) ON public.finetune_metrics_history TO odyn_ingest_ro;
GRANT SELECT (id, user_id, reservation_state) ON public.gpu_reservations TO odyn_ingest_ro;
GRANT SELECT (provider, sku, intake_type, usd_per_hour) ON public.gpu_baseline_rates TO odyn_ingest_ro;
GRANT SELECT (id, provider) ON public.nodes TO odyn_ingest_ro;
GRANT SELECT (gpu_key, node_id, gpu_model_class) ON public.gpu_inventory TO odyn_ingest_ro;
GRANT SELECT (id, user_id, status) ON public.ray_clusters TO odyn_ingest_ro;
GRANT SELECT (id, cluster_id, node_id) ON public.ray_cluster_workers TO odyn_ingest_ro;
GRANT SELECT (container_id, gpu_key, assigned_at) ON public.container_gpu_assignments TO odyn_ingest_ro;
GRANT SELECT (
  job_id,
  gpu_identifiers,
  node_ids,
  gpu_reservation_id,
  gpu_model_class,
  min_gpu_vram_gb,
  num_workers,
  price_book_hourly_rate_usd,
  lifecycle_attempt
) ON public.ingest_job_placement_v1 TO odyn_ingest_ro;

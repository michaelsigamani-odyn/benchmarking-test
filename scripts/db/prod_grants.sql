-- Production grant script (source-of-truth snapshot).
-- Contains statement timeout guards and the 14 granted objects.

SET lock_timeout = '5s';
SET statement_timeout = '30s';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odyn_ingest_ro') THEN
    CREATE ROLE odyn_ingest_ro NOLOGIN;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO odyn_ingest_ro;

GRANT SELECT ON public.ray_train_jobs TO odyn_ingest_ro;
GRANT SELECT ON public.post_training_workloads TO odyn_ingest_ro;
GRANT SELECT ON public.scheduler_workload_requests TO odyn_ingest_ro;
GRANT SELECT ON public.finetune_billing_intervals TO odyn_ingest_ro;
GRANT SELECT ON public.job_cost_summary TO odyn_ingest_ro;
GRANT SELECT ON public.finetune_metrics_history TO odyn_ingest_ro;
GRANT SELECT ON public.gpu_reservations TO odyn_ingest_ro;
GRANT SELECT ON public.gpu_baseline_rates TO odyn_ingest_ro;
GRANT SELECT ON public.nodes TO odyn_ingest_ro;
GRANT SELECT ON public.gpu_inventory TO odyn_ingest_ro;
GRANT SELECT ON public.ray_clusters TO odyn_ingest_ro;
GRANT SELECT ON public.ray_cluster_workers TO odyn_ingest_ro;
GRANT SELECT ON public.container_gpu_assignments TO odyn_ingest_ro;
GRANT SELECT ON public.ingest_job_placement_v1 TO odyn_ingest_ro;

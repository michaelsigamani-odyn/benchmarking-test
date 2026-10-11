-- Read-only ingest role grants for Postgres -> GCS -> BigQuery extractor.
-- Source of truth for grant-derived column config.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odyn_ingest_ro') THEN
    CREATE ROLE odyn_ingest_ro NOLOGIN;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO odyn_ingest_ro;

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

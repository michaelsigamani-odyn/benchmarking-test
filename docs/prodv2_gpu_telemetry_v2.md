# prodv2 GPU Telemetry v2 (BigQuery + Vast snapshot)

> Superseded by v3 rollout assets:
> - `ddl_telemetry_prodv2_v3.sql`
> - `scripts/db/gpu_telemetry_validation_v3.sql`
> - `docs/prodv2_gpu_telemetry_v3_runbook.md`

This change set adds a stricter telemetry model that addresses:

1. **prodv2-only machine scope**
2. **duplicate-row control + explicit dedup checks**
3. **host-telemetry-service-only ingestion filter**
4. **intuitive telemetry object names and rounded float formatting**

## Files added/updated

- `ddl_telemetry_prodv2_v2.sql`
  - Creates `fleet_ops` dataset and telemetry views with intuitive names
  - Adds `clean_ops.prodv2_machine_registry_v1`
  - Adds deduped raw sample view: `raw_ops.machine_gpu_telemetry_samples_dedup_v2`
  - Adds strict prodv2 + host-service telemetry view: `clean_ops.machine_gpu_telemetry_prodv2_v2`
  - Adds latest/overview/summary views under `fleet_ops`
- `scripts/db/bq_dedup_checks.sql`
  - Assertion-based duplicate checks for raw/clean telemetry/workload tables
- `scripts/benchmark_bq_ingest_v1.py`
  - Adds post-load duplicate checks for the existing benchmark ingest tables
- `scripts/vast_offers_snapshot_v2.py`
  - Pulls Vast offers via CLI
  - Loads key from GCP Secret Manager when needed
  - Normalizes column naming and rounds floating-point values
  - Deduplicates output rows before writing snapshot files

## Run order

```bash
# 1) Apply prodv2 telemetry model
bq query --nouse_legacy_sql < ddl_telemetry_prodv2_v2.sql

# 2) Run duplicate assertions
bq query --nouse_legacy_sql < scripts/db/bq_dedup_checks.sql
```

If `gcloud`/`bq` returns reauthentication errors, refresh auth first:

```bash
gcloud auth login
```

## Vast snapshot run

`scripts/vast_offers_snapshot_v2.py` expects either:

- `VASTAI_API_KEY` / `VAST_API_KEY` already set, **or**
- GCP secret lookup inputs:
  - `VAST_GCP_PROJECT`
  - `VAST_GCP_SECRET_NAME`

Defaults if unset:

- project: `project-dalia`
- secret: `VASTAI_API_KEY`

Example:

```bash
scripts/run_vast_offers_snapshot_v2.sh \
  --query 'external=false rentable=true verified=true' \
  --limit 200 \
  --output-dir outputs/vast
```

Outputs:

- `outputs/vast/vast_offers_raw_<timestamp>.json`
- `outputs/vast/vast_offers_normalized_<timestamp>.json`
- `outputs/vast/vast_offers_normalized_<timestamp>.jsonl`

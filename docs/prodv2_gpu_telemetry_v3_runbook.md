# prodv2 GPU telemetry v3 runbook

## Scope

This runbook executes the prodv2 telemetry model and validation flow across:

- edge host agents + ingest
- cloud control-plane inventory snapshots
- governed BigQuery fleet reconciliation and alert views

## Prerequisites

1. GCP auth (BigQuery + Cloud Run + Secret Manager):

```bash
gcloud auth login
```

2. AWS auth (extractor dependencies: Postgres secret + KMS HMAC):

```bash
aws login
```

3. Confirm required credentials are present in shell environment used for rollout.

## Deployment order

### Step 1 — edge ingest prerequisites

Apply edge agent columns first:

```bash
bq query --nouse_legacy_sql < /Users/michaelsigamani/odyn-private/edge_telemetry/ddl_edge_agent_columns.sql
```

Deploy/verify edge ingest service and token secret per:

- `/Users/michaelsigamani/odyn-private/edge_telemetry/README.md`

### Step 2 — edge agent rollout

Install on edge machines with systemd timer:

```bash
sudo bash /Users/michaelsigamani/odyn-private/edge_telemetry/install_edge_agent.sh <INGEST_URL> <TOKEN_FILE>
```

Canary first, then full edge rollout.

### Step 3 — prodv2 telemetry model rollout (BQ)

From this repo root:

```bash
bash scripts/run_gpu_telemetry_rollout_v3.sh
```

This applies:

- `ddl_telemetry_prodv2_v3.sql`
- `scripts/db/bq_dedup_checks.sql`
- `scripts/db/gpu_telemetry_validation_v3.sql`
- `scripts/db/gpu_telemetry_reconciliation_v3.sql`

Logs are written to `outputs/gpu_telemetry_rollout_v3/`.

## Validation mapping (A–G)

`scripts/db/gpu_telemetry_validation_v3.sql` includes:

- **A** London edge freshness + coverage
- **B** prodv2 cloud freshness + coverage
- **C** Mac independence evidence (`edge-agent:*` vs laptop-run IDs)
- **D** collector restart indicator
- **E** retry/dedup duplicate checks
- **F** fleet reconciliation (machine + GPU)
- **G** dashboard/readiness row counts + null-key checks

## Alert integration targets

Wire these alert views into existing notifier jobs (Slack/email):

- `fleet_ops.alert_gpu_ingest_stop_v1`
- `fleet_ops.alert_gpu_stale_or_not_reporting_v1`
- `fleet_ops.alert_gpu_collector_restarts_v1`
- `fleet_ops.alert_gpu_faults_sustained_v1`
- `fleet_ops.alert_gpu_coverage_drop_v1`

## Required evidence artifacts

Capture and archive:

1. Fleet inventory reconciliation output (machine + GPU expected/reporting)
2. Rollout logs from `outputs/gpu_telemetry_rollout_v3/`:
   - `ddl_apply_*.log`
   - `dedup_checks_*.log`
   - `validation_*.log`
   - `reconciliation_*.log`
3. Latest validation query output for tests A–G
4. Alert snapshot output (same validation script)
5. Tableau readiness checks (row counts + null-key checks)

When live access is temporarily unavailable, generate a local evidence snapshot from already-captured artifacts:

```bash
python3 scripts/build_gpu_telemetry_evidence_from_artifacts.py
```

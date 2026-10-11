# First Dry Run Runbook (No Secrets)

This runbook is for a **local/tunnel dry run** and a **GCS canary**.

## 1) Prerequisites

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Generate/refresh the prod sample config from grant-generated columns:

```bash
.venv/bin/python scripts/db/generate_prod_config_from_generated.py
```

## 2) Prepare environment

Set AWS profile for Secrets Manager/KMS:

```bash
export AWS_PROFILE=odyn-ingest
```

Set DSN host/user/port/database in env (no password in DSN):

```bash
export ODYN_REPLICA_DSN='postgresql://odyn_ingest_ro@127.0.0.1:15432/marketplace'
```

Password source at runtime (pick one):

- Option A: let extractor fetch password from Secrets Manager (`odyn/ingest-ro-db`, `us-west-2`) via `AWS_PROFILE`.
- Option B: set `PGPASSWORD` in env (still not in DSN or config file):

```bash
export PGPASSWORD='set-at-runtime'
```

For canary using ADC impersonation (no JSON key file):

```bash
gcloud auth application-default login \
  --impersonate-service-account=pg-landing-writer@dahlia-507808.iam.gserviceaccount.com
```

## 3) Dry run (no sink writes)

```bash
.venv/bin/python scripts/pg_state_extractor_v0.py \
  --config config/pg_state_extractor_v0.prod.sample.json \
  --dry-run \
  --limit-per-table 5000
```

Expected output (per table):

- `TABLE <schema.table>`
- `COLUMNS: ...`
- `SOURCE_COUNT: ...`
- `SAMPLE_REDACTED_ROW: ...`
- `FINDINGS_COUNT: ...`
- `DROPPED_KEYS: ...`
- `DROPPED_ARRAY_ELEMENTS: ...`
- stderr info line like:
  - `INFO effective_sslmode=prefer connection_encrypted=false ...`

## 4) Canary (writes only one object)

```bash
.venv/bin/python scripts/pg_state_extractor_v0.py \
  --config config/pg_state_extractor_v0.prod.sample.json \
  --canary
```

Expected output:

- JSON with `status=ok`
- `object` path like `_canary/<run_id>.json`

No table reads/writes are performed in canary mode.

## 5) What alert/failure looks like

Alert run (success with findings):

- stderr: `ALERT run_id=<...> findings_count=<n>`
- process exit code: `20`

No-alert success:

- process exit code: `0`

Failure:

- stderr: `ERROR: ...`
- process exit code: `1`

TLS enforcement failure example (if config uses `sslmode=require` but backend is unencrypted):

- `ERROR: sslmode=require but backend connection is not encrypted`

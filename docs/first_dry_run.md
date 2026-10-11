# First Dry Run Runbook (No Secrets)

## 1) Install extractor deps

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r extractor/requirements-extractor.txt
```

## 2) Open SSM tunnel to Postgres

```bash
aws ssm start-session \
  --target i-REPLACE_ME \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["REPLICA_HOST"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

## 3) Environment

Use DSN without password:

```bash
export ODYN_REPLICA_DSN='postgresql://odyn_ingest_ro@127.0.0.1:15432/marketplace'
export AWS_PROFILE=odyn-ingest
```

Password source at runtime (choose one):

- `PGPASSWORD` env var, or
- Secrets Manager `odyn/ingest-ro-db` in `us-west-2`.

KMS key ARN source (`us-west-2`) should be read from a file at runtime (no hardcoded secret values):

```bash
export KMS_KEY_ARN="$(cat /ABSOLUTE/PATH/kms_hmac_key_arn.txt)"
```

## 4) ADC impersonation for canary (no key file)

Service account:

- `pg-landing-writer@inbound-dahlia-507808-g1.iam.gserviceaccount.com`

Required role on that SA:

- `roles/iam.serviceAccountTokenCreator`

```bash
gcloud auth application-default login \
  --impersonate-service-account=pg-landing-writer@inbound-dahlia-507808-g1.iam.gserviceaccount.com
```

## 5) Print grants-derived skeleton for review

```bash
.venv/bin/python scripts/pg_state_extractor_v0.py \
  --config config/pg_state_extractor_v0.prod.sample.json \
  --print-granted-config
```

## 6) Dry run (no sink writes, absolute state dir)

```bash
.venv/bin/python scripts/pg_state_extractor_v0.py \
  --config config/pg_state_extractor_v0.prod.sample.json \
  --dry-run \
  --state-dir /ABSOLUTE/PATH/.pg_state_store \
  --limit-per-table 5000
```

Expected:

- Per-table block with: `TABLE`, `COLUMNS`, `SOURCE_COUNT`, `SAMPLE_REDACTED_ROW`, `FINDINGS_COUNT`.
- SSL telemetry line on stderr (for tunnel config):
  - `INFO effective_sslmode=prefer connection_encrypted=false ...`

## 7) Canary run (single object only)

```bash
.venv/bin/python scripts/pg_state_extractor_v0.py \
  --config config/pg_state_extractor_v0.prod.sample.json \
  --state-dir /ABSOLUTE/PATH/.pg_state_store \
  --canary
```

Expected:

- JSON response with `_canary/<run_id>.json` object path.
- No table snapshot files are written.

## 8) Exit behavior / failures

- No-alert success: exit code `0`
- Alert success: exit code `20`, stderr includes `ALERT run_id=... findings_count=...`
- Failure: exit code `1`, stderr includes `ERROR: ...`
- TLS hard fail (if config says `sslmode=require` and backend is not encrypted):
  - `ERROR: sslmode=require but backend connection is not encrypted`

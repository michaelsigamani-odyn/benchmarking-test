#!/usr/bin/env bash
set -euo pipefail

source ~/.bashrc >/dev/null 2>&1 || true

PROJECT_ID="${PROJECT_ID:-inbound-dahlia-507808-g1}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/gpu_telemetry_rollout_v3}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$OUTPUT_DIR"

bq --project_id="$PROJECT_ID" query --nouse_legacy_sql < ddl_telemetry_prodv2_v3.sql \
  > "$OUTPUT_DIR/ddl_apply_${TS}.log"

bq --project_id="$PROJECT_ID" query --nouse_legacy_sql < scripts/db/bq_dedup_checks.sql \
  > "$OUTPUT_DIR/dedup_checks_${TS}.log"

bq --project_id="$PROJECT_ID" query --nouse_legacy_sql < scripts/db/gpu_telemetry_validation_v3.sql \
  > "$OUTPUT_DIR/validation_${TS}.log"

bq --project_id="$PROJECT_ID" query --nouse_legacy_sql < scripts/db/gpu_telemetry_reconciliation_v3.sql \
  > "$OUTPUT_DIR/reconciliation_${TS}.log"

printf 'Rollout logs written to %s\n' "$OUTPUT_DIR"

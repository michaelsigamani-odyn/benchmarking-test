#!/usr/bin/env bash
set -euo pipefail

source ~/.bashrc >/dev/null 2>&1 || true

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
BQ_LOCATION="${BQ_LOCATION:-EU}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is not set and gcloud project is unavailable" >&2
  exit 1
fi

export TOGETHER_API_KEY="${TOGETHER_API_KEY:-${TOGETHERAI_API_KEY:-}}"

python3 scripts/benchmark_bq_ingest_v1.py \
  --project "${PROJECT_ID}" \
  --location "${BQ_LOCATION}" \
  --prefer-live-together \
  --eks-csv "/Users/michaelsigamani/Desktop/kuberay_jobs_sep01_to_now.csv"

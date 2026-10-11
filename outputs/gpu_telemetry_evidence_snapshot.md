# GPU telemetry evidence snapshot (artifact-derived)

Generated: `2026-10-11T21:03:37.474956+00:00`

## Authoritative inventory counts (pg snapshot dry-run)

- `public.nodes` source count: **22**
- `public.gpu_inventory` source count: **37**

## Edge raw telemetry (30d)

- total rows: **2715**
- distinct hosts: **7**
- distinct host+gpu: **8**
- min/max sample ts: `2026-10-11 06:49:16` / `2026-10-11 15:10:46`

## Edge cadence (30m)

- host+gpu with recent samples: **6**
- median interval seconds: **60**
- p90 interval seconds: **333**

## Edge machine freshness summary

- hosts total: **7**
- hosts fresh <=30s: **5**
- hosts fresh <=2m: **5**
- max age seconds: **16343**

## Production fact telemetry status

- `clean_ops.fact_gpu_telemetry_v1` total rows (365d): **0**
- `clean_ops.fact_gpu_telemetry_1m_v1` total rows (365d): **0**

## Notes

This report is built from existing local evidence artifacts and does not perform live BigQuery/API calls.
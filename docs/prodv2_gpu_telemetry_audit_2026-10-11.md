# prodv2 GPU telemetry audit (2026-10-11)

## Outcome

The current production telemetry stack is **partially deployed**:

- Edge has active telemetry writes in BigQuery.
- Cloud/prodv2 telemetry is present in control-plane heartbeat paths, but not yet represented in `clean_ops.fact_gpu_telemetry_v1`.
- Mac prototype collection still exists and still writes to the same raw edge table.

This audit is based on code + existing evidence artifacts available locally.

## 1) Current collectors and ingestion paths

### Edge prototype (Mac-driven)

- File: `/Users/michaelsigamani/odyn-private/edge_gpu_sampler.py`
- Evidence:
  - Explicitly marked prototype on Mac: lines 3-4
  - Writes to `raw_ops.edge_gpu_samples_v1`: lines 9, 36
  - Uses direct `bq insert`: lines 274-277

### Edge autonomous host agent (target architecture)

- File: `/Users/michaelsigamani/odyn-private/edge_telemetry/edge_agent.py`
- Evidence:
  - Designed for per-machine timer execution: lines 3, 13
  - Sends HTTPS payload with bearer token: lines 8, 214-223
  - Retry loop in agent: lines 244-249
- Installer/runtime:
  - `/Users/michaelsigamani/odyn-private/edge_telemetry/install_edge_agent.sh`
  - 60s timer and boot-safe service: lines 52-60

### Edge ingest service (Cloud Run)

- File: `/Users/michaelsigamani/odyn-private/edge_telemetry/edge_ingest/main.py`
- Evidence:
  - Writes to BigQuery with row IDs for idempotency: lines 257-265
  - Request validation, token auth, dedup key generation: lines 95-164, 205-253

### Cloud/prodv2 node telemetry source

- Node-agent collection:
  - `/Users/michaelsigamani/Documents/DevelopmentCode/active-orchestrator/node-agent/internal/core/monitor.go`
  - `/Users/michaelsigamani/Documents/DevelopmentCode/active-orchestrator/node-agent/internal/core/monitor_amd.go`
- Node-agent heartbeat stream:
  - `/Users/michaelsigamani/Documents/DevelopmentCode/active-orchestrator/node-agent/internal/grpc/client.go` lines 665-891
- Control-plane ingestion:
  - `/Users/michaelsigamani/Documents/DevelopmentCode/active-orchestrator/control-plane/internal/grpcserver/server.go` lines 385-556

## 2) Authoritative inventory sources identified

- `public.nodes` and `public.gpu_inventory` in control-plane Postgres (extracted via `pg_state_snapshot_v1` pipeline)
- `clean_ops.edge_machine_registry_v1` for edge host registry
- External provider catalog available from `public.gpu_baseline_rates` snapshot (provider/SKU baseline), with real-time offers via provider APIs (control-plane external inventory service)

## 3) Available reporting evidence snapshot

From `/Users/michaelsigamani/odyn-private/dryrun_output.txt`:

- `public.nodes` source count: **22** (lines 73-78)
- `public.gpu_inventory` source count: **37** (lines 82-87)

From `outputs/bigquery_table_report.md`:

- `raw_ops.edge_gpu_samples_v1` has active data (last 30 days):
  - rows: **2715**
  - distinct hosts: **7**
  - distinct host+gpu: **8**
  - lines 2682-2693
- `clean_ops.edge_machine_state_v2` freshness summary:
  - `hosts_total=7`, `hosts_fresh_le_2m=5`, `max_age_s=16343`
  - lines 2708-2717
- `clean_ops.fact_gpu_telemetry_v1` rows in last 365 days: **0**
  - lines 2656-2666

## 4) Confirmed gaps

1. **Mac dependency not fully decommissioned**
   - Prototype Mac sampler is still present and writes to production raw edge telemetry table.

2. **Cloud/prodv2 telemetry not reflected in governed production fact table**
   - `fact_gpu_telemetry_v1` is empty in the available report snapshot.

3. **Freshness classes required by rollout objective are not yet standardized across all fleet planes**
   - Existing edge view uses state labels (`NO_RECENT_SAMPLE`, `GPU_FAULT`, etc.) but not the required global class set (`Reporting/Stale/Not reporting/Unknown`).

4. **Alerting is not yet represented as governed alert-ready views for all required scenarios**
   - Ingest stop, stale transitions, sustained faults, and coverage-drop were not found as centralized BQ alert views in this repo baseline.

## 5) Blockers to live validation in this session

- BigQuery access requires non-interactive auth refresh (`bq` returned reauthentication failure).
- AWS credentials are currently unavailable for live extractor reruns (`aws sts get-caller-identity` failed).

## 6) Implemented remediation assets in this repo

- `ddl_telemetry_prodv2_v3.sql`
  - Builds authoritative prodv2 registry from pg snapshots + edge registry
  - Unifies edge+cloud telemetry
  - Adds required freshness classes and reconciliation views
  - Adds alert-ready views
- `scripts/db/gpu_telemetry_validation_v3.sql`
  - Query pack for rollout tests A-G and alert snapshots
- `scripts/db/gpu_telemetry_reconciliation_v3.sql`
  - Machine-level and GPU-level reconciliation extract for evidence packaging
- `scripts/run_gpu_telemetry_rollout_v3.sh`
  - Applies v3 DDL + duplicate checks + validation query pack

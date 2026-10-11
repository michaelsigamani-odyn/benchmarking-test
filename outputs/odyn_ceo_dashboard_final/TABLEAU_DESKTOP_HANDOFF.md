# Tableau Desktop Native Rebuild Handoff (Authoring-Only)

Use this document to complete the workbook **only in Tableau Desktop UI**.

> Status note: the **minimal workbook is approved**, but the full six-domain executive dashboard is **not yet complete**.

## Design intent (from approved mockup)

Primary executive question:

- **Are we operating reliably, using our GPUs efficiently, and building a cost advantage?**

Use this structure in Tableau:

- Top-row KPI cards for immediate state visibility.
- Time-series trend where applicable (utilisation/concurrency context).
- Outcome visuals for completed vs failed with OOM explicitly called out.
- Estimation accuracy with underestimation rates and confidence intervals.
- Fleet health/diversity plus drill-down access.
- Operational drill tables for engineering investigation.

## Mockup caveat (must remain explicit)

- The design mockup is **illustrative** and not a validated rendering of every point/value.
- Placeholder visuals must not be presented as measured production results.
- Missing commercial, VRAM-quality, and scheduler-economics measurements must remain visibly **N/A / Unavailable**.

## Constraints

- Do **not** do XML editing/generation.
- Keep existing exported datasets unchanged.
- Build from the approved baseline workbook and finish presentation only.

## Baseline workbook

- Approved minimal package:
  - `outputs/odyn_ceo_dashboard_final/native_rebuild_starter/ODYN_CEO_Dashboard_minimal_native.twbx`

## Data mode label (required)

Add visible dashboard text:

- `Data mode: Static BigQuery snapshot (packaged CSV)`
- `Extraction timestamp: 2026-10-11 10:48:58`

## Exact datasource mappings

All files are in:

- `outputs/odyn_ceo_dashboard_final/native_rebuild_starter/`

### Domain sheets

1. `domain_1_commercial.csv` → KPI Domain 1 (Commercial)
2. `domain_2_util_reliability.csv` → KPI Domain 2 (Util/Reliability)
3. `domain_3_digester_quality.csv` → KPI Domain 3 (Digester quality)
4. `domain_4_estimation_pricing.csv` → KPI Domain 4 (Estimation/Pricing)
5. `domain_5_fleet_health.csv` → KPI Domain 5 (Fleet health)
6. `domain_6_scheduler_economics.csv` → KPI Domain 6 (Scheduler economics)

### Drilldown sheets

- `machine_drilldown_snapshot.csv` → machine summary drill source
- `job_drilldown_snapshot.csv` → job summary drill source

### Raw drill detail sources (required)

- `machine_detail_raw.csv`
- `machine_overview_raw.csv`
- `job_investigation_raw.csv`

## Required fields

### Domain/snapshot datasets

For these files:

- `ceo_dashboard_snapshot.csv`
- `domain_1_commercial.csv` … `domain_6_scheduler_economics.csv`
- `machine_drilldown_snapshot.csv`
- `job_drilldown_snapshot.csv`

Required columns:

- `Snapshot_TS`
- `KPI_Domain`
- `KPI_Metric`
- `KPI_Detail`
- `KPI_Count`
- `KPI_Value`

### Machine raw fields (minimum for detail)

From `machine_detail_raw.csv`:

- `host`, `sample_ts`, `gpu_index`, `gpu_status`, `util_gpu_pct`, `vram_pct`, `power_w`, `temp_c`, `workload_id`

From `machine_overview_raw.csv`:

- `host`, `state`, `telemetry_status`, `machine_health_state`, `last_sample_ts`, `expected_gpus`, `gpu_rows`, `demo_readiness`

### Job raw fields (minimum for detail)

From `job_investigation_raw.csv`:

- `workload_id`, `provider`, `workload_type`, `submitted_at`, `wall_time_min`, `outcome_status`, `failure_class`, `failure_message_redacted`, `assigned_gpus`

## Worksheet build recipe (native Tableau)

Use this naming exactly so dashboard placement/actions stay clear.

### Executive cards

1. `Executive Cards`
   - Data source: `ceo_dashboard_snapshot.csv`
   - Filter `KPI_Domain` to six summary domains only (`D1...D6`)
   - Rows: `KPI_Domain`, `KPI_Metric`
   - Text: `KPI_Value`
   - Tooltip: `KPI_Detail`, `Snapshot_TS`
   - Color rule: if `KPI_Detail` contains `UNAVAILABLE` or `NOT_MONITORED`, use neutral/gray.

### Domain sections

2. `KPI 1 Commercial`
   - Source: `domain_1_commercial.csv`
   - Show metric/value table with `KPI_Metric` + `KPI_Value`
   - Always display `KPI_Detail` as subtitle/tooltip for N/A rationale.

3. `KPI 2 Util Reliability`
   - Source: `domain_2_util_reliability.csv`
   - Primary: metric cards for concurrency/failure/telemetry status.
   - Optional supporting trend: create from `machine_detail_raw.csv` using `sample_ts` + `util_gpu_pct` (avg).
   - Add reference line at 50% where a utilization trend is shown.

4. `KPI 3 Digester Quality`
   - Source: `domain_3_digester_quality.csv`
   - Keep unavailable VRAM/LangSmith explicitly N/A from `KPI_Detail`.

5. `KPI 4 Estimation Pricing`
   - Source: `domain_4_estimation_pricing.csv`
   - Show MAPE and underestimation values from `KPI_Value`.
   - Add annotation text (from validated reconciliation):
     - Runtime underestimation 95% CI: `69.28%–90.91%`
     - Cost underestimation 95% CI: `66.83%–89.35%`

6. `KPI 5 Fleet Health`
   - Source: `domain_5_fleet_health.csv`
   - Include machine-health/fleet-coverage summary cards.
   - Optional diversity visual from `machine_overview_raw.csv` (`vendor`, `expected_gpus`, `gpu_rows`).

7. `KPI 6 Scheduler Economics`
   - Source: `domain_6_scheduler_economics.csv`
   - Keep non-measured economics explicitly N/A via `KPI_Detail`.

### Drilldown sheets

8. `Machine Drill Summary`
   - Source: `machine_drilldown_snapshot.csv`
   - Show one row per machine metric.
   - Calculated key: `MachineHostKey = REPLACE([KPI_Metric], ' gpu_rows', '')`

9. `Machine Drill Detail`
   - Source: `machine_detail_raw.csv` (optionally blend with `machine_overview_raw.csv` by `host`)
   - Required columns in view: `host`, `sample_ts`, `gpu_index`, `gpu_status`, `util_gpu_pct`, `vram_pct`, `power_w`, `temp_c`, `workload_id`

10. `Job Drill Summary`
    - Source: `job_drilldown_snapshot.csv`
    - Calculated key: `JobWorkloadKey = REPLACE([KPI_Metric], ' wall_time_min', '')`

11. `Job Drill Detail`
    - Source: `job_investigation_raw.csv`
    - Required columns in view: `workload_id`, `provider`, `workload_type`, `wall_time_min`, `outcome_status`, `failure_class`, `failure_message_redacted`, `assigned_gpus`

## Dashboard layout (required)

Create these dashboards:

1. `CEO Executive Dashboard`
   - Place 7 worksheets:
     - `Executive Overview`
     - `KPI 1 Commercial`
     - `KPI 2 Util Reliability`
     - `KPI 3 Digester Quality`
     - `KPI 4 Estimation Pricing`
     - `KPI 5 Fleet Health`
     - `KPI 6 Scheduler Economics`

2. `CEO Drilldown Dashboard`
   - Place 4 worksheets:
     - `Machine Drill Summary` (from `machine_drilldown_snapshot.csv`)
     - `Machine Drill Detail` (from `machine_detail_raw.csv` + optional `machine_overview_raw.csv`)
     - `Job Drill Summary` (from `job_drilldown_snapshot.csv`)
     - `Job Drill Detail` (from `job_investigation_raw.csv`)

## Interactivity requirements

Configure dashboard interactions so executive-to-operator flow works without SQL changes:

- Selecting provider/model/domain context filters related sheets.
- Selecting failure category filters to impacted job rows.
- Selecting machine summary row filters machine detail rows.
- Selecting job summary row filters job detail rows.

## Filter-action configuration (required)

### Machine drill action

Create calculated field in `Machine Drill Summary`:

- `MachineHostKey = REPLACE([KPI_Metric], ' gpu_rows', '')`

Then Dashboard Action Filter:

- Source sheet: `Machine Drill Summary`
- Target sheet: `Machine Drill Detail`
- Run action: Select
- Target filter: Selected Fields
  - Source `MachineHostKey` → Target `host`

### Job drill action

Create calculated field in `Job Drill Summary`:

- `JobWorkloadKey = REPLACE([KPI_Metric], ' wall_time_min', '')`

Then Dashboard Action Filter:

- Source sheet: `Job Drill Summary`
- Target sheet: `Job Drill Detail`
- Run action: Select
- Target filter: Selected Fields
  - Source `JobWorkloadKey` → Target `workload_id`

### Additional recommended filter actions (same dashboard)

- Source: `Machine Drill Detail` → Target: `Machine Drill Summary` (bidirectional context)
- Source: `Job Drill Detail` → Target: `Job Drill Summary` (bidirectional context)
- Clear selection behavior: show all values.

## KPI availability display rules

- Use `KPI_Detail` to show status (`MEASURED`, `UNAVAILABLE`, `NOT_MONITORED`, etc.).
- Do **not** render unavailable/missing values as zero.
- Keep the reliability label explicit:
  - `Observed Digester cohort: 12/58 failed (20.69%)` (not fleet-wide).

## Smart Digester validated values to preserve

From validated KPI reconciliation (`kpi_summary.json`):

- Completed jobs `N = 46`
- Runtime MAPE `% = 73.52`
- Cost MAPE `% = 74.12`
- Runtime underestimation `% = 82.61`
- Cost underestimation `% = 80.43`
- Runtime underestimation Wilson 95% CI: `69.28%–90.91%`
- Cost underestimation Wilson 95% CI: `66.83%–89.35%`

Show CI values in tooltip/subtitle or a KPI annotation on Domain 4.

## Final save target

- `ODYN_CEO_Dashboard_full_native.twbx`

This should be produced by native Tableau authoring and then visually validated in Tableau Desktop.

## Final visual acceptance checklist

- Workbook opens without data-source warnings.
- `CEO Executive Dashboard` exists and renders all six KPI domain sections.
- `CEO Drilldown Dashboard` exists and renders machine/job summary + detail views.
- Machine summary click filters machine detail rows.
- Job summary click filters job detail rows.
- Missing commercial / VRAM-quality / scheduler-economics values are visibly `N/A`/`Unavailable`.
- Reliability callout is labeled as **Observed Digester cohort** (not fleet-wide).
- Dashboard header includes static snapshot mode + extraction timestamp.

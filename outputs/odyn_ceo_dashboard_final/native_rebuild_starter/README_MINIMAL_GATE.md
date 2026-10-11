# Minimal Acceptance Gate (Tableau-native)

Use this folder only for the **first gate** workbook.

## Files

- `ceo_dashboard_snapshot.csv` (executive KPI snapshot)
- `tableau_ceo_fleet_machine_detail_v1.csv` (machine drill source for later phase)
- `tableau_ceo_job_investigation_v1.csv` (job drill source for later phase)

## Build in Tableau Desktop

1. New Workbook.
2. Connect to `ceo_dashboard_snapshot.csv`.
3. Build worksheet `Executive KPI (Snapshot)`:
   - Rows: `KPI_Domain`, `KPI_Metric`
   - Marks/Text: `KPI_Value`
   - Tooltip/Detail: `KPI_Detail`
   - Filter `KPI_Domain` to only:
     - D1 Commercial
     - D2 Util/Reliability
     - D3 Digester quality
     - D4 Estimation
     - D5 Fleet
     - D6 Scheduler econ
4. Create dashboard `CEO Dashboard (Minimal)` and place that worksheet on it.
5. Add title text:
   - `Data mode: Packaged CSV Snapshot`
   - `Snapshot timestamp: 2026-10-11 10:48:58`
6. Save as packaged workbook:
   - `ODYN_CEO_Dashboard_minimal_native.twbx`

## Important

- Keep unavailable KPIs shown via `KPI_Detail` status text (do not convert to 0).
- This gate uses static CSV snapshots, not live BigQuery or live telemetry.

## Next phase files (for six-domain extension)

After minimal gate acceptance, use these CSVs in this same folder to extend `ceo-dash.twb` natively:

- `domain_1_commercial.csv`
- `domain_2_util_reliability.csv`
- `domain_3_digester_quality.csv`
- `domain_4_estimation_pricing.csv`
- `domain_5_fleet_health.csv`
- `domain_6_scheduler_economics.csv`
- `machine_drilldown_snapshot.csv`
- `job_drilldown_snapshot.csv`

Raw drill datasets are also included (not only KPI summary rows):

- `machine_detail_raw.csv`
- `machine_overview_raw.csv`
- `job_investigation_raw.csv`

Use these raw files for detailed drill sheets/actions.

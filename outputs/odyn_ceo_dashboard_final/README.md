# ODYN CEO Dashboard — Open, Navigate, Refresh

## 1) Workbook files

- **Minimal approved baseline (opens):**
  - `native_rebuild_starter/ODYN_CEO_Dashboard_minimal_native.twbx`
- **Attempted full package target:**
  - `ODYN_CEO_Dashboard_full_native.twbx`

## 2) How to open

1. Open Tableau Desktop.
2. Use **File → Open**.
3. Select either workbook above.

## 3) Current status

- `ODYN_CEO_Dashboard_minimal_native.twbx` is the stable baseline.
- The current full package attempt fails to load with Tableau error **2805CF18**:
  - `Dashboard references sheet ‘Machine Drill Sheet’ which has no visual representation in the workbook.`
  - In alternate draft variants the same error appears with `Machine Drilldown`.

See `VALIDATION_REPORT.md` for full evidence.

## 4) Snapshot data mode and timestamp

This dashboard package is **snapshot-based**, not live:

- **Data mode:** Static BigQuery snapshot (packaged CSV)
- **Extraction timestamp:** `2026-10-11 10:48:58 UTC`

The workbook does **not** auto-refresh from BigQuery.

## 5) Refreshing the snapshot data (manual)

To refresh with new data, replace the packaged CSVs with new exports and rebuild the `.twbx` package.
Current packaged sources are under:

- `outputs/odyn_ceo_dashboard_final/native_rebuild_starter/*.csv`
- `outputs/odyn_ceo_dashboard_final/data/*.csv`

## 6) What is required for live BigQuery refreshes

To make this workbook live instead of snapshot-only, Tableau authoring must be updated to:

1. Replace CSV-based data sources with governed BigQuery connections.
2. Rebind worksheet fields to BigQuery tables/views.
3. Configure credentials/authentication for Tableau Desktop/Server.
4. Validate all dashboards and drill actions against live sources.
5. Publish with scheduled extract/refresh (or live connection policy).

## 7) Authoritative build handoff

- `TABLEAU_DESKTOP_HANDOFF.md`

That file remains the source of truth for required worksheet naming, dashboards, and drilldown actions.

# Native Authoring Assets (Analytically Correct Rebuild Inputs)

This folder contains precomputed Tableau-ready CSVs and specs for rebuilding the CEO dashboard with correct semantics and screenshot-aligned visual hierarchy.

## Build/rebuild assets

Run:

```bash
python outputs/odyn_ceo_dashboard_final/native_authoring_assets/build_native_authoring_assets.py
```

## Key files

- `semantic_kpi_model.csv` — KPI definitions (unit, aggregation, coverage, status)
- `executive_kpi_cards.csv` — six top-card metrics
- `gpu_utilization_timeseries.csv` — utilization trend + 50% reference
- `workload_outcomes_by_week.csv` / `oom_failure_breakdown.csv`
- `commercial_comparability.csv` — explicit N/A comparability evidence
- `digester_availability_cards.csv` — N/A cards with coverage proof
- `estimation_accuracy_summary.csv` — validated 46-job cohort KPIs
- `runtime_scatter_points.csv` / `cost_scatter_points.csv`
- `fleet_health_overview.csv` / `fleet_gpu_model_distribution.csv` / `provider_coverage.csv`
- `machine_drill_records.csv` / `machine_gpu_telemetry_records.csv`
- `job_drill_records.csv` / `unmatched_predictions.csv`
- `scheduler_economics_status.csv`

## Authoring + QA docs

- `NATIVE_TABLEAU_VISUAL_SPEC.md` — exact native worksheet/dashboard design spec
- `IMPLEMENTATION_CHECKLIST_NATIVE.md` — execution checklist
- `ANALYTICAL_BASELINE_REPORT.md` — computed metric validation
- `kpi_guardrail_checks.json` — key metric consistency checks (MAPE/underestimation/N.A. rules)
- `render_validation_checklist_template.csv` — worksheet QA template for rendered checks
- `DELIVERY_REPORT.md` — completion/blocker summary for this run
- `manifest.sha256.json` — file-integrity manifest for the asset pack

Bundle archive (for handoff/import):

- `outputs/odyn_ceo_dashboard_final/native_authoring_assets_bundle.zip`

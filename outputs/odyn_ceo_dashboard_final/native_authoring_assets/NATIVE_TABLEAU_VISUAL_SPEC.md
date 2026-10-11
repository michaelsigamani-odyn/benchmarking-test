# Native Tableau Visual Spec — Executive Rebuild (Screenshot-Matched)

This spec is for **native Tableau authoring** (Tableau Cloud or Tableau Desktop edit mode), not XML editing.

It uses curated assets in this folder to prevent unit-mixing and false-zero errors.

Apply formatting from `VISUAL_STYLE_TOKENS.md` for screenshot-level parity.

## 1) Data sources to add in Tableau

Use these CSVs as separate data sources:

- `executive_kpi_cards.csv`
- `gpu_utilization_timeseries.csv`
- `concurrency_timeline.csv`
- `workload_outcomes_by_week.csv`
- `oom_failure_breakdown.csv`
- `commercial_comparability.csv`
- `digester_availability_cards.csv`
- `estimation_accuracy_summary.csv`
- `runtime_scatter_points.csv`
- `cost_scatter_points.csv`
- `fleet_health_overview.csv`
- `fleet_gpu_model_distribution.csv`
- `provider_coverage.csv`
- `machine_drill_records.csv`
- `machine_gpu_telemetry_records.csv`
- `job_drill_records.csv`
- `unmatched_predictions.csv`
- `scheduler_economics_status.csv`

## 2) Dashboard structure (match screenshot visual hierarchy)

### Dashboard: `CEO Executive Dashboard`

Recommended fixed size: `1600 x 1800` (or equivalent cloud layout preserving card spacing).

#### Header row

- Left: title `Company Pulse`
- Subtitle: `Executive health signals with operator-ready lineage and refresh context`
- Right chips:
  - `Static snapshot · Local packaged sources`
  - `Filters`
  - `Rolling 12 weeks` (text parameter control)

#### Row 1: six headline KPI cards

Use one tile per record from `executive_kpi_cards.csv` (sorted by `card_order`).

Card fields:

- Title: `card_title`
- Main number: `value_display`
- Status dot/label: `status`
- Coverage line: `coverage_display`
- Freshness line: `freshness_ts`
- Tooltip: `detail_note`

Style target:

- White background, 10–14px corner radius, subtle border.
- Main number bold, large, dark navy.
- Status color semantics:
  - `MEASURED` green
  - `PARTIAL` amber
  - `UNAVAILABLE` gray

#### Row 2 left: utilization + momentum section

Worksheet A: `GPU Utilization Trend vs 50% Reference`

- Source: `gpu_utilization_timeseries.csv`
- Chart: line
- X: `sample_ts`
- Y: `avg_gpu_utilization_pct`
- Reference line: constant `50` from `reference_line_pct`
- Tooltip: utilization %, coverage %, sample_rows/util_rows
- Subtitle: indicate edge-only telemetry coverage.

Worksheet B: `Concurrent GPU Jobs and Users (Event Timeline)`

- Source: `concurrency_timeline.csv`
- Chart: dual-axis line or layered line (separate axis labels if dual-axis)
- Never place users and jobs on hidden unlabeled axis.

#### Row 2 right: revenue-outlook analog replaced with valid operational summary

Worksheet C: `Workload Outcome Mix (Matched Digester Jobs)`

- Source: `workload_outcomes_by_week.csv`
- Chart: stacked bars by `year_week`
- Measures: `completed_jobs`, `failed_jobs`, `stopped_jobs`
- Tooltip includes `total_jobs`, `success_rate_pct`.

Worksheet D: `Failure Diagnostics (OOM vs Non-OOM)`

- Source: `oom_failure_breakdown.csv`
- Chart: stacked bar by week, color by `failure_bucket`
- Keep OOM as explicit category.

#### Middle row: domain evidence panels

1. **Commercial comparison validity**
   - Source: `commercial_comparability.csv`
   - If `comparison_supported=false`, show N/A card and explanatory table.
   - No USD axis if no measured USD values exist.

2. **Estimation/pricing accuracy**
   - KPI cards from `estimation_accuracy_summary.csv`:
     - Runtime MAPE `73.52%`
     - Cost MAPE `74.12%`
     - Runtime underestimation `82.61%`
     - Cost underestimation `80.43%`
   - Scatterplots:
     - `runtime_scatter_points.csv` (`predicted_runtime_hours` vs `actual_runtime_hours`)
     - `cost_scatter_points.csv` (`estimated_total_cost_usd` vs `actual_operational_cost_usd`)

3. **Digester quality availability**
   - Source: `digester_availability_cards.csv`
   - Display two N/A cards with coverage evidence.
   - Do not substitute missing values with zero.

#### Fleet section (visual intent aligned to screenshot 2)

Worksheet E: `Fleet Status Funnel (Registered → Reporting → Healthy)`

- Source: `provider_coverage.csv`
- Use `edge` row as measured path.
- Show `production` as N/A status, not zero bar.

Worksheet F: `GPU Model Distribution and Coverage`

- Source: `fleet_gpu_model_distribution.csv`
- Chart: treemap or stacked bars by `gpu_model`, colored by `vendor`
- Tooltip: expected_gpu_count, reporting_gpu_count, telemetry_coverage_pct.

Worksheet G: `Machine Health Table`

- Source: `fleet_health_overview.csv`
- Include full `host` (no truncation where identification matters).

#### Navigation / action links

- Add navigation buttons:
  - `Open Machine Investigation`
  - `Open Job Investigation`

Actions should route to `CEO Drilldown Dashboard`.

---

### Dashboard: `CEO Drilldown Dashboard`

Top-left: `Machine Drill Summary` (from `machine_drill_records.csv`)

- One row per host with health/coverage and utilization summaries.
- Full host ID visible.

Top-right: `Job Drill Summary` (from `job_drill_records.csv`)

- One row per workload/job.
- Columns: provider, workload_type, model_id, wall_time, status.

Bottom-left: `Machine GPU Telemetry Detail` (from `machine_gpu_telemetry_records.csv`)

- Record-level GPU telemetry table; no generic KPI metric/value bars.

Bottom-right: `Job Detail + Prediction Diagnostics`

- Source: `job_drill_records.csv`
- Include runtime/cost prediction diagnostics and failure context.

Optional panel: `Unmatched Predictions` from `unmatched_predictions.csv`.

## 3) Field-level semantic rules (must enforce)

- Never plot `%`, `count`, `USD`, `hours`, and `tokens` on a common axis.
- Never sum percentages or MAPE values.
- Use means only where mathematically valid and cohort-defined.
- Missing data:
  - show `N/A`/`Unavailable`
  - do not coerce null → 0.

## 4) Required chart titles and axis labels

Use question-style titles:

- `Are GPUs utilized above the 50% operating threshold over time?`
- `How are matched workloads distributed across completed, failed, and stopped outcomes?`
- `Where do failed workloads come from: OOM or non-OOM causes?`
- `How far do runtime and cost estimates deviate from actuals?`
- `Which machines are stale, degraded, or missing telemetry?`

Axis labels must include units:

- `%`, `USD`, `Hours`, `Jobs`, `Machines`, `GPUs`.

## 5) Render QA protocol (after native authoring)

Complete `render_validation_checklist_template.csv` for each worksheet after visual render inspection in Tableau.

Each sheet must pass:

1. Business question clarity
2. Correct unit/axis
3. Valid aggregation math
4. Backed by underlying records
5. Truthful missing-data handling
6. Legible and useful visual design

## 6) Freshness and sample size annotations (required)

Every KPI and domain panel should display:

- Cohort/sample size (e.g., `N=46`)
- Coverage denominator (e.g., `7/83 observed`)
- Freshness timestamp from source row

This is mandatory for analytical transparency.

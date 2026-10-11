# Worksheet Build Map (Native Tableau)

This is the exact worksheet inventory to build in Tableau UI.

## Executive dashboard worksheets

### 1) `KPI Card - Workload Success`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = workload_success_rate`
- Mark: Text
- Text: `value_display`
- Tooltip: `coverage_display`, `freshness_ts`, `detail_note`

### 2) `KPI Card - Avg GPU Utilization`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = avg_gpu_utilization`
- Mark: Text

### 3) `KPI Card - Peak Concurrency`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = peak_concurrency`
- Mark: Text

### 4) `KPI Card - Completed Jobs`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = completed_jobs`
- Mark: Text

### 5) `KPI Card - Edge Coverage`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = edge_telemetry_coverage`
- Mark: Text

### 6) `KPI Card - Commercial Comparability`
- Source: `executive_kpi_cards.csv`
- Filter: `card_key = commercial_comparison`
- Mark: Text
- Ensure neutral N/A styling when `status = UNAVAILABLE`

### 7) `GPU Utilization Trend vs 50%`
- Source: `gpu_utilization_timeseries.csv`
- Columns: `sample_ts` (continuous)
- Rows: `avg_gpu_utilization_pct`
- Mark: Line
- Add reference line at value `50`
- Tooltip: `util_coverage_pct`, `sample_rows`, `util_rows`

### 8) `Concurrency Timeline`
- Source: `concurrency_timeline.csv`
- Columns: `ts` (continuous)
- Rows: `concurrent_gpu_jobs`
- Add second axis or separate pane for `concurrent_users`
- Mark: Line
- Do not hide units when dual-axis is used.

### 9) `Workload Outcomes by Week`
- Source: `workload_outcomes_by_week.csv`
- Columns: `year_week`
- Rows: Measure Values (`completed_jobs`, `failed_jobs`, `stopped_jobs`)
- Mark: Stacked Bar

### 10) `OOM Breakdown by Week`
- Source: `oom_failure_breakdown.csv`
- Columns: `year_week`
- Rows: `jobs`
- Color: `failure_bucket`
- Mark: Stacked Bar

### 11) `Commercial Comparability Evidence`
- Source: `commercial_comparability.csv`
- Mark: Text table
- Rows: `workload_type`, `model_id`
- Columns: `odyn_rows`, `together_rows`, `odyn_cost_rows`, `together_cost_rows`, `status`
- Tooltip: `na_reason`

### 12) `Digester Availability Cards`
- Source: `digester_availability_cards.csv`
- Mark: Text (2 cards)
- Text: `metric`, `status`, `coverage_n`, `coverage_denominator`, `explanation`

### 13) `Estimation KPI Cards`
- Source: `estimation_accuracy_summary.csv`
- Mark: Text
- Rows: `metric`
- Text: `value_display`
- Tooltip: `sample_size_n`, `denominator_note`, `ci_low_pct`, `ci_high_pct`

### 14) `Runtime Predicted vs Actual`
- Source: `runtime_scatter_points.csv`
- Columns: `predicted_runtime_hours`
- Rows: `actual_runtime_hours`
- Mark: Circle
- Color: `runtime_underestimate_flag`
- Add diagonal reference line `y=x`

### 15) `Cost Predicted vs Actual`
- Source: `cost_scatter_points.csv`
- Columns: `estimated_total_cost_usd`
- Rows: `actual_operational_cost_usd`
- Mark: Circle
- Color: `cost_underestimate_flag`
- Add diagonal reference line `y=x`

### 16) `Fleet Coverage by Plane`
- Source: `provider_coverage.csv`
- Columns: `plane`
- Rows: `telemetry_coverage_pct`
- Mark: Bar
- Color by `coverage_status`
- Label production as N/A when value null.

### 17) `GPU Model Distribution`
- Source: `fleet_gpu_model_distribution.csv`
- Option A: Treemap using `expected_gpu_count`
- Option B: Stacked bar by `gpu_model`, color by `vendor`

### 18) `Machine Health Overview`
- Source: `fleet_health_overview.csv`
- Text table with full `host`
- Include: `state`, `machine_health_state`, `telemetry_status`, `last_sample_ts`, `expected_gpus`, `gpu_rows`

### 19) `Scheduler Economics Status`
- Source: `scheduler_economics_status.csv`
- Text table / status cards
- Show explicit `UNAVAILABLE` rows and `note`

## Drilldown dashboard worksheets

### 20) `Machine Drill Summary`
- Source: `machine_drill_records.csv`
- Include full host and health/status fields

### 21) `Machine GPU Telemetry Detail`
- Source: `machine_gpu_telemetry_records.csv`
- Detailed telemetry table (sample_ts, gpu_index, util, vram, power, temp)

### 22) `Job Drill Summary`
- Source: `job_drill_records.csv`
- Table with workload, provider, model, workload_type, wall_time, status

### 23) `Job Drill Detail`
- Source: `job_drill_records.csv`
- Diagnostics columns: predicted/actual runtime and cost fields, error rates

### 24) `Unmatched Predictions` (optional panel)
- Source: `unmatched_predictions.csv`

## Required dashboard actions

1. `Machine Drill Summary` -> `Machine GPU Telemetry Detail`
   - Source field: `host`
   - Target field: `host`

2. `Job Drill Summary` -> `Job Drill Detail`
   - Source field: `workload_id`
   - Target field: `workload_id`

3. Clear selection behavior: show all values.

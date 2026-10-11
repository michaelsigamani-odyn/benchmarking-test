# Native Tableau Rebuild Checklist (Visual + Analytical)

Use this with `NATIVE_TABLEAU_VISUAL_SPEC.md`.

## A. Semantic model gate (before any chart build)

- [ ] Import `semantic_kpi_model.csv`
- [ ] Confirm each KPI has one unit family (%, count, USD, hours)
- [ ] Confirm missing metrics remain `UNAVAILABLE` (not 0)
- [ ] Confirm sample-size and coverage text fields are present in tooltips/labels

## B. Executive dashboard build

- [ ] Build six KPI cards from `executive_kpi_cards.csv`
- [ ] Build utilization line from `gpu_utilization_timeseries.csv` with 50% reference line
- [ ] Build concurrency timeline from `concurrency_timeline.csv`
- [ ] Build workload outcome stacked bars from `workload_outcomes_by_week.csv`
- [ ] Build OOM diagnostic stacked bars from `oom_failure_breakdown.csv`
- [ ] Add commercial N/A panel using `commercial_comparability.csv`
- [ ] Add estimation KPI cards from `estimation_accuracy_summary.csv`
- [ ] Add runtime and cost scatterplots from `runtime_scatter_points.csv` and `cost_scatter_points.csv`
- [ ] Add digester availability N/A cards from `digester_availability_cards.csv`
- [ ] Add fleet funnel/coverage from `provider_coverage.csv`
- [ ] Add GPU distribution from `fleet_gpu_model_distribution.csv`
- [ ] Add machine health table from `fleet_health_overview.csv`

## C. Domain-specific requirements

### Commercial
- [ ] Show USD per million tokens **only if measured data exists**
- [ ] Otherwise show N/A + reason + comparable-pair counts

### Utilization / reliability
- [ ] Separate utilization (%), concurrency (counts), and outcomes (counts)
- [ ] No mixed-unit axis

### Digester quality
- [ ] Show VRAM and LangSmith status as N/A cards with coverage context

### Estimation / pricing
- [ ] Separate KPI cards for Runtime MAPE 73.52%, Cost MAPE 74.12%
- [ ] Separate underestimation cards: runtime 82.61%, cost 80.43%
- [ ] Include CI in tooltip/subtitle

### Fleet
- [ ] Machine health by host
- [ ] GPU model distribution by vendor
- [ ] Provider/plane coverage panel (edge measured, production N/A)

### Scheduler
- [ ] Measured economics only if present
- [ ] Else N/A explanation from `scheduler_economics_status.csv`

## D. Drill-down build

- [ ] Machine summary from `machine_drill_records.csv`
- [ ] Machine telemetry detail from `machine_gpu_telemetry_records.csv`
- [ ] Job summary from `job_drill_records.csv`
- [ ] Job detail from `job_drill_records.csv`
- [ ] Optional unmatched predictions table from `unmatched_predictions.csv`
- [ ] Configure actions: machine host → machine detail, workload_id → job detail

## E. Visual parity checks (against screenshots)

- [ ] Header + subtitle hierarchy matches
- [ ] Card spacing and rounded panel style match
- [ ] Section composition mirrors reference: cards → trends/outcomes → diagnostic tables
- [ ] Fleet section has at-a-glance summary plus distribution view

## F. Analytical QA (rendered view)

Complete `render_validation_checklist_template.csv`.

- [ ] Every worksheet answers a clear business question
- [ ] Axis labels and units are correct
- [ ] Aggregation is mathematically valid
- [ ] Underlying records match displayed marks
- [ ] Missing data is truthfully represented
- [ ] Visual readability is acceptable

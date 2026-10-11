# Analytical Baseline Report (Pre-Render)

This report validates KPI semantics and data coverage from packaged snapshot sources before native Tableau chart authoring.

## Snapshot context

- Snapshot inspection timestamp: `2026-10-11 10:48:58`
- Mode: static packaged CSV

## Executive metrics computed from governed extracts

| KPI | Value | Unit | Cohort / denominator | Status |
|---|---:|---|---|---|
| Workload success rate (matched jobs) | 69.70 | % | 46 completed / 66 matched | MEASURED |
| Average GPU utilization (edge util rows) | 0.00 | % | 35 util rows / 100 telemetry rows | MEASURED |
| Peak concurrent GPU jobs | 7 | jobs | 32 concurrency events | MEASURED |
| Completed jobs (estimation cohort) | 46 | jobs | completed matched rows with actual runtime/cost | MEASURED |
| Edge telemetry coverage | 71.43 | % | 5 reporting machines / 7 registered | MEASURED |
| Commercial comparability (cost-per-million) | N/A | USD / 1M tokens | 0/6 comparable pairs with measured cost fields | UNAVAILABLE |

## Estimation/pricing validated cohort

- Completed matched jobs with actual runtime/cost: `N=46`
- Runtime MAPE: `73.52%`
- Cost MAPE: `74.12%`
- Runtime underestimation rate: `82.61%` (Wilson 95% CI: `69.28%–90.91%`)
- Cost underestimation rate: `80.43%` (Wilson 95% CI: `66.83%–89.35%`)

## Missing/Unavailable evidence (must stay N/A)

### Commercial

- `cost_per_million_tokens_usd` is null across all rows.
- Limitation reason present: missing governed token_count + governed pricing join.

### Digester quality

- VRAM observed rows: `7 / 83` (insufficient for executive-quality metric stability in this snapshot).
- LangSmith evaluation rows: `0`.

### Scheduler economics

- Throughput, supplier cost, buyer price, margin columns are all null (`0 measured rows`).

## Reliability/failure context

- Matched runtime cohort statuses: 46 completed, 12 failed, 8 stopped.
- Failed/stopped jobs: 20 total.
- OOM failures in failed/stopped set: 5 (25.0%).

## Fleet coverage context

- Edge plane row present and measured.
- Production plane row present but metrics empty in snapshot; must be displayed as N/A.

## Output assets produced

All curated sources were generated in:

- `outputs/odyn_ceo_dashboard_final/native_authoring_assets/`

These include semantic model, KPI cards, trend/scatter datasets, domain N/A status cards, and drilldown-ready machine/job records.

## Render-validation status

Analytical baseline is complete, but **render QA is pending native Tableau authoring access**.

Use:

- `NATIVE_TABLEAU_VISUAL_SPEC.md`
- `IMPLEMENTATION_CHECKLIST_NATIVE.md`
- `render_validation_checklist_template.csv`

to complete worksheet-by-worksheet rendered validation.

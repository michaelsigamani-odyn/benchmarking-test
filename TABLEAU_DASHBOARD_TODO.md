# Odyn CEO Dashboard - Tableau Cloud Implementation

## TODO List

### Phase 1: Environment Setup and Analysis
- [x] Identify Tableau Cloud environment (browser-based Tableau Online)
- [x] Access the published workbook at: https://prod-uk-a.online.tableau.com/#/site/michaelsigamani-0f23db8efb/workbooks/3962203/views
- [x] Review current dashboard structure
- [x] Identify available data sources and fields
- [x] Check permissions for editing

### Phase 2: Executive Dashboard Implementation
- [ ] Implement KPI cards for:
  - Workload success rate
  - Average GPU utilisation
  - Peak concurrent users and jobs
  - Completed fine-tuning jobs
  - Fleet telemetry coverage
  - Commercial competitiveness versus Together AI
- [ ] Ensure all 6 executive KPIs render coherently in a visually polished way

### Phase 3: Six KPI Domains Implementation
- [ ] Implement Commercial competitiveness section
  - Compare Odyn vs Together AI cost and pricing per million tokens
  - Use matched model/workload comparisons where data exists
- [ ] Implement GPU utilisation and reliability section
  - Utilisation over time
  - Peak concurrency
  - Workload success/failure rates
  - OOM failures and failure reasons
- [ ] Implement Smart Digester quality section
  - VRAM prediction accuracy
  - Predicted versus observed VRAM
  - LangSmith hallucination evaluation results
- [ ] Implement Estimation and pricing accuracy section
  - Runtime MAPE, cost MAPE
  - Underestimation rates, confidence intervals
  - Predicted-versus-actual comparisons
  - Preserve the validated 46-job cohort
- [ ] Implement Fleet health and compute diversity section
  - Machine health
  - NVIDIA/AMD coverage
  - GPU models, cloud providers, locations
  - Telemetry coverage and reporting freshness
- [ ] Implement Scheduler economics section
  - Realised cost per million useful tokens
  - Placement efficiency
  - Alternative placement costs and potential savings

### Phase 4: Visualization Quality
- [ ] Apply appropriate chart types for each domain:
  - KPI cards for headline metrics
  - Line charts for trends
  - Bar charts for comparisons
  - Outcome breakdowns for workloads
  - Scatterplots for prediction accuracy
  - Detailed tables for machines/jobs
- [ ] Implement clear titles, axis labels, and units for all charts
- [ ] Ensure consistent color semantics across all visuals
- [ ] Add tooltips and explanations for all metrics
- [ ] Show data-source and sample-size context

### Phase 5: Drill-Down Functionality
- [ ] Implement machine drill-down dashboard
  - Hostname, GPU model and count, provider and location
  - GPU utilisation, health, reporting status
  - Last telemetry observation
  - Distinguish machines from GPUs and unknown telemetry
- [ ] Implement job drill-down dashboard
  - Job ID, model, workload type
  - Completion/failure status, failure reason
  - Runtime, estimated vs observed metrics
- [ ] Test machine selection triggering correct details
- [ ] Test job selection triggering correct records

### Phase 6: Data Integrity
- [ ] Preserve existing KPI definitions and metrics
- [ ] Maintain sample sizes and confidence intervals
- [ ] Respect distinction between production/edge telemetry
- [ ] Maintain cost/price distinctions (estimated costs, measured costs, customer prices)
- [ ] Keep static snapshot extraction timestamp
- [ ] Never invent data or replace missing data with zero
- [ ] Where evidence is unavailable, show N/A with explanation

### Phase 7: Validation and Testing
- [ ] Save workbook after each meaningful change
- [ ] Test all filters and drill-down actions
- [ ] Check for missing visualisations, broken fields and datasource errors
- [ ] Resolve Error `2805CF18` specifically
- [ ] Verify all dashboards open without errors

### Phase 8: Final Export and Delivery
- [ ] Export final packaged workbook as `ODYN_CEO_Dashboard_full_native.twbx`
- [ ] Verify export completeness and portability
- [ ] Preserve original CSV exports and KPI reconciliation files
- [ ] Produce comprehensive validation report covering all AC
- [ ] Provide final deliverable and screenshots/evidence

### Phase 9: Cleanup
- [ ] Verify final exported workbook is safely preserved
- [ ] Delete temporary Tableau Cloud workbook (ID 3962203) when delivery confirmed
- [ ] Remove temporary project resources
- [ ] Revoke temporary access where authorized
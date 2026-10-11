# Odyn CEO Dashboard Implementation Plan

## Overview
This document provides a comprehensive implementation plan for creating an executive dashboard in Tableau Cloud that displays key business metrics for Odyn Network's GPU fleet. The dashboard must present reliability, utilization, commercial competitiveness, and operational efficiency metrics in an interactive, visually polished manner.

## Implementation Approach

### Phase 1: Environment Setup and Analysis
1. **Access the published workbook**:
   - Navigate to: https://prod-uk-a.online.tableau.com/#/site/michaelsigamani-0f23db8efb/workbooks/3962203/views
   - Verify you can access and edit the workbook
   - Check available data sources and fields

2. **Understand the data structure**:
   - Identify key dimensions (machine, job, workload, model, provider, GPU type)
   - Identify key metrics (utilization, success rates, costs, runtime)
   - Determine available date ranges and snapshot timestamps

### Phase 2: Executive Dashboard Implementation

#### KPI Card Layout Requirements:
All KPI cards should follow consistent visual design with:
- Clear metric names
- Large, readable values with appropriate units
- Target indicators or thresholds
- Tooltips with explanations
- Color-coded status indicators (green/yellow/red)

#### Required KPIs:
1. **Workload Success Rate**:
   - Formula: (Completed Jobs / Total Jobs) * 100
   - Target: >95%
   - Add year-over-year comparison

2. **Average GPU Utilisation**:
   - Formula: Average of GPU Utilization (%) by machine
   - Target: >70%
   - Show current vs historical trend

3. **Peak Concurrent Users and Jobs**:
   - Metric: Maximum concurrent jobs count (rolling window)
   - Display peak values over time period
   - Show current values with trend line

4. **Completed Fine-tuning Jobs**:
   - Count of jobs with workload type = "fine-tuning"
   - Show total count and trend
   - Include success/failure breakdown

5. **Fleet Telemetry Coverage**:
   - Formula: ( Machines with telemetry / Total Machines) * 100
   - Target: >90%
   - Show breakdown by provider/type

6. **Commercial Competitiveness vs Together AI**:
   - Cost per million tokens comparison
   - Use matched model/workload data where available
   - Visual: Side-by-side bar chart or trend line

### Phase 3: Six KPI Domain Implementation

#### 1. Commercial Competitiveness
- Create a visualization comparing cost-per-million-tokens between Odyn and Together AI
- Match models and workloads where possible for fair comparison
- Show price trends over time
- Add tooltips explaining data sources and assumptions
- Include N/A for unmatched comparisons

#### 2. GPU Utilisation and Reliability
- Line chart: GPU Utilization over time (last 30 days)
- Bar chart: Workload success/failure rates
- Pie chart: OOM failure reasons breakdown
- Scatterplot: Peak concurrency vs utilization correlation
- Add filters for time range, machine type, provider

#### 3. Smart Digester Quality
- Scatterplot: Predicted VRAM vs Actual VRAM
- Accuracy metric: MAPE for VRAM predictions
- Bar chart: LangSmith hallucination scores by model
- Trend line showing prediction quality improvement
- Include confidence intervals

#### 4. Estimation and Pricing Accuracy
- Line chart: Runtime MAPE over time
- Bar chart: Cost MAPE by model/workload type
- Scatterplot: Estimated vs Actual Runtime/Cost
- Include confidence intervals for predictions
- Show 46-job cohort with established metrics preserved

#### 5. Fleet Health and Compute Diversity
- Heatmap: Machine health status (green/yellow/red)
- Bar chart: GPU model distribution vs provider
- Map visualization: Fleet locations
- Table: Telemetry freshness by machine
- Stacked bar charts: NVIDIA vs AMD coverage
- Filter by provider, location, uptime

#### 6. Scheduler Economics
- Line chart: Realised cost per million tokens
- Bar chart: Placement efficiency vs alternative costs
- Table: Potential savings vs solution type
- Scatterplot: Cost savings vs performance impact
- Include filters for time period, cluster type

### Phase 4: Visualization Quality Standards

#### Design Principles:
1. **Consistency**: Use consistent fonts, colors, and chart styles
2. **Contrast**: Ensure text is readable against backgrounds
3. **Clarity**: Every element has a purpose and is not redundant
4. **Interactivity**: Include tooltips, filters, and drill-down capabilities
5. **Accessibility**: Colorblind-friendly palettes

#### Chart Types:
- **KPI Cards**: For key metrics that need immediate attention
- **Line Charts**: For trends over time (utilization, cost, success rates)
- **Bar Charts**: For comparisons across categories (providers, GPUs, models)
- **Scatterplots**: For prediction accuracy and correlation analysis
- **Heatmaps**: For evaluating multiple factors simultaneously
- **Tables**: For detailed listings with filtering capabilities

#### All Visual Elements:
- Clear, descriptive titles (not just "Chart 1")
- Appropriate axis labels with units
- Logical scale ranges and domains
- Meaningful tooltips with supporting data
- Legends that are clear and helpful
- Consistent color schemes (e.g., green for success, red for failure)
- Proper data source identification

### Phase 5: Drill-Down Functionality

#### Machine Drill-Down Dashboard:
1. **Machine Details Panel**:
   - Hostname, GPU model and count
   - Provider and location
   - Current GPU utilisation percentage
   - Health status indicators
   - Last telemetry observation timestamp
   - Online/offline status differentiation

2. **Machine Interaction**:
   - Selection in any chart should highlight corresponding machine
   - Clicking a machine should open detailed machine view
   - Include filters by provider, location, GPU type

#### Job Drill-Down Dashboard:
1. **Job Details Panel**:
   - Job ID, model name, workload type
   - Completion status and timestamp
   - Failure reason (if applicable)
   - Runtime and estimated vs actual
   - Cost estimation and actual costs
   - Provider and machine used

2. **Job Interaction**:
   - Selection should open job details panel
   - Clicking on a job should filter details
   - Include filters by model, workload type, date range

### Phase 6: Data Integrity Validation

#### Rules:
1. **Preserve Operational Definitions**:
   - Maintain distinction between production and edge telemetry
   - Preserve sample sizes for statistical validity
   - Maintain confidence intervals for all estimates
   - Keep static snapshot extraction timestamp

2. **Data Handling Rules**:
   - Never invent data or replace missing values with zeros
   - Show "N/A" with detailed explanation when data unavailable
   - Use existing KPI definitions precisely
   - Respect cost/price classifications: estimated costs, measured costs, customer prices

3. **Data Sources**:
   - Link all visualizations to underlying BigQuery exports
   - Validate reconciliation artifacts are used correctly
   - Ensure provenance tracking for every metric shown

### Phase 7: Validation Processes

#### Routine Checks:
1. **After every meaningful change**:
   - Save the workbook
   - Reopen dashboard in Tableau Cloud
   - Confirm all worksheets render correctly
   - Test all filters and drilling actions
   - Check for missing visualizations or broken fields
   - Debug error 2805CF18 specifically

2. **Specific Error Prevention**:
   - Prevention of "Dashboard references a sheet with no visual representation"
   - Ensure all sheets have appropriate visualizations
   - Only embed sheets that are clearly visualized

#### Testing Scenarios:
- Edit filters and confirm the impact on all dependent visuals
- Test drill-down between dashboard views
- Verify tooltips display proper content
- Test interactions across all visual elements
- Confirm all KPI cards update correctly with filters

### Phase 8: Export and Delivery

#### Final Steps:
1. **Export Preparation**:
   - Save final workbook in Tableau Cloud
   - Export as `ODYN_CEO_Dashboard_full_native.twbx` format
   - Verify exported file contains all views and is portable

2. **Documentation**:
   - Preserve original CSV exports
   - Preserve KPI reconciliation files
   - Create validation report covering all AC
   - Include screenshots or visual evidence

#### Acceptance Criteria Verification:
- All 6 executive KPIs render coherently in < 30 seconds
- All 6 KPI domains are fully navigable
- All visualizations follow design reference
- Machine and job drill-down works correctly
- Data integrity is maintained
- All validation checks pass
- Final export is complete and portable

### Phase 9: Cleanup Protocol

#### Post-Delivery Actions:
1. **Confirmation of Success**:
   - Verify final exported workbook is safely preserved
   - Confirm delivery was successful

2. **Resource Management**:
   - Delete only the temporary workbook (ID: 3962203)
   - Remove any temporary project resources
   - Revoke temporary access where authorized

3. **Quality Assurance**:
   - Confirm all cleanups completed without affecting main workbook
   - Document successful cleanup steps taken

## Key Implementation Notes

1. **User Experience**:
   - Keep dashboard to 1-screen view with scrolling for extended content
   - Create a clear visual hierarchy with properly spaced sections
   - Use consistent branding and color themes
   - Ensure first-time users understand dashboard content within 30 seconds

2. **Technical Consistency**:
   - Use the same data formats and naming conventions across sheets
   - Maintain consistent date ranges for all time series
   - Apply same color schemes to same concepts across different charts
   - Use consistent filter navigation between sheets

3. **Performance Optimization**:
   - Add appropriate data aggregation where necessary
   - Use parameters for common time filters
   - Minimize unnecessary calculations in visualizations
   - Test with sample dataset before full implementation

This implementation guide can be followed by a Tableau user with access to the published workbook to complete the dashboard according to all acceptance criteria.
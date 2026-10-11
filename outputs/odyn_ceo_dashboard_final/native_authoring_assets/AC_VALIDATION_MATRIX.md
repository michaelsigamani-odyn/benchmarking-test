# Acceptance Criteria Validation Matrix

Status legend:

- ✅ Passed from data/semantic validation
- ⏳ Pending native render validation
- 🚫 Blocked (needs Tableau Cloud/Desktop interactive authoring session)

## 1) Semantic data model

- ✅ KPI semantic definitions completed in `semantic_kpi_model.csv`
- ✅ Unit separation enforced in curated sources
- ✅ Coverage/sample-size columns included
- ✅ Measured vs unavailable explicit status fields included

## 2) Executive overview design

- ⏳ Visual implementation pending native authoring using `NATIVE_TABLEAU_VISUAL_SPEC.md`
- ✅ Required KPI values and panel datasets prepared

## 3) Six domain replacements

- ✅ Domain datasets prepared with measured vs N/A logic
- ⏳ Native worksheet construction pending

## 4) Drill-down rebuild

- ✅ Machine/job record-level datasets prepared:
  - `machine_drill_records.csv`
  - `machine_gpu_telemetry_records.csv`
  - `job_drill_records.csv`
- ⏳ Native action/filter wiring pending Tableau authoring

## 5) Visual standards

- ✅ Titles/axis/unit requirements specified in `NATIVE_TABLEAU_VISUAL_SPEC.md`
- ⏳ Rendered tooltip/legibility validation pending

## 6) Analytical correctness QA

- ✅ Baseline calculations validated in `ANALYTICAL_BASELINE_REPORT.md`
- ⏳ Worksheet render QA template created: `render_validation_checklist_template.csv`
- 🚫 Final rendered QA cannot be completed from CLI-only environment without Tableau interactive authoring access.

## 7) Delivery workflow

- ✅ Native authoring asset package produced (`README.md` in this folder)
- 🚫 Final cloud workbook export, screenshot evidence, and temporary workbook deletion require Tableau interactive access and credentials.

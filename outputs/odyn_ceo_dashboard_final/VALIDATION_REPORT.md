# Validation Report — Odyn CEO Tableau Dashboard

Date: 2026-10-11

## Scope

Validation against the requested acceptance criteria for:

- `outputs/odyn_ceo_dashboard_final/ODYN_CEO_Dashboard_full_native.twbx`

using Tableau Desktop (not XML-only checks).

---

## Result summary

- **Overall status: BLOCKED / NOT COMPLETE**
- Root blocker: Tableau Desktop load error **2805CF18** on full dashboard variants:
  - `Dashboard references sheet ‘Machine Drill Sheet’ which has no visual representation in the workbook.`
  - Also observed as `Machine Drilldown` in alternate draft variants.
  - Also observed as `Machine Drill Summary` after structural rewrite attempts.

Prior blocker **D2E8DA72** (manual-sort / shelf-sorts / devicelayouts parse errors) was repaired, but 2805CF18 persists.

Because the workbook does not load successfully, full visual and interaction validation cannot be completed.

---

## Evidence captured

### Tableau Desktop environment

- App present: `/Applications/Tableau Desktop (Apple silicon) 2026.2.app`
- Logs location: `~/Documents/My Tableau Repository/Logs/log.txt`

### Logged load failure evidence

From Tableau log (`log.txt`):

- `detailed-error-msg` with help link error code `2805cf18`
- short message:
  - `Dashboard references sheet ‘Machine Drill Sheet’ which has no visual representation in the workbook.`
  - equivalent variants encountered during fixes:
    - `Machine Drilldown`
    - `Machine Drill Summary`

### Parse-error repair evidence

The previous full draft (`ODYN_CEO_Dashboard_full_native_draft.twbx`) raised `D2E8DA72` schema errors on:

- `manual-sort`
- `shelf-sorts`
- empty `devicelayouts`

Those were removed/repaired in the rebuilt workbook lineage, and the parse-stage error no longer appears. The remaining blocker is the machine-drill worksheet visual representation error.

### Packaged workbook checks

- `native_rebuild_starter/ODYN_CEO_Dashboard_full_native_draft_v5.twbx` contains multiple `.twb` entries (including `machine_sheet_only_test.twb`), which is non-ideal packaging.
- A cleaned package was produced with a single `.twb`:
  - `ODYN_CEO_Dashboard_full_native.twbx`
- Despite clean packaging, Tableau still reports 2805CF18 on full-dashboard variants.

---

## Acceptance criteria status

## AC1 — A Real, Working Tableau Dashboard

- **Status: FAIL**
- Reason: full workbook load still fails in Tableau Desktop with 2805CF18 (machine drill sheet visual representation).

## AC2 — Executive Overview

- **Status: NOT VERIFIED**
- Reason: full workbook does not load; executive dashboard cannot be validated end-to-end.

## AC3 — Six Complete KPI Domains

- **Status: NOT VERIFIED**
- Reason: full workbook blocked at load.

## AC4 — Professional Data Visualisation

- **Status: NOT VERIFIED**
- Reason: full workbook blocked at load.

## AC5 — Functional Drill-Downs

- **Status: FAIL**
- Reason: dashboard load failure specifically references machine drill sheet visual representation.

## AC6 — Data Integrity and Transparency

- **Status: PARTIAL**
- Snapshot data artifacts and timestamp are preserved; however, full workbook render validation is blocked.

## AC7 — Actual Tableau Validation

- **Status: FAIL**
- Tableau Desktop was used, and failure was observed directly.
- Required successful render/drill validations cannot be completed while 2805CF18 persists.

## AC8 — Final Deliverables

- `ODYN_CEO_Dashboard_full_native.twbx` — **Produced, but not passing AC1/AC7**
- `README.md` — **Produced**
- `VALIDATION_REPORT.md` — **Produced**
- Source CSVs and reconciliation artifacts — **Preserved**

---

## Exact intervention required to unblock completion

Open the workbook in Tableau Desktop authoring UI and repair the invalid drilldown sheet/dashboard references so that:

1. `CEO Drilldown Dashboard` references only worksheets that Tableau recognizes as valid visual sheets.
2. Machine and job drill sheets are rebuilt/renamed per the handoff spec:
   - `Machine Drill Summary`
   - `Machine Drill Detail`
   - `Job Drill Summary`
   - `Job Drill Detail`
3. Drill filter actions are recreated and tested.
4. Workbook is saved as `ODYN_CEO_Dashboard_full_native.twbx` and re-opened cleanly with no load errors.

Without that Tableau-native UI repair, this task cannot be truthfully marked complete.

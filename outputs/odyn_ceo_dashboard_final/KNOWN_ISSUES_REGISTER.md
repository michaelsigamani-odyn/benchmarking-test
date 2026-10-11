# Known Issues Register — Tableau Dashboard Build

**Last Updated:** 2026-10-11  
**Maintained by:** Autonomous validation agent

---

## Issue: 2805CF18 — "Dashboard references sheet 'X' which has no visual representation in the workbook"

### Error Details
- **Error Code:** `2805CF18`
- **Error Message:** `Dashboard references sheet 'Executive Overview' which has no visual representation in the workbook.`
- **Variants Observed:**
  - `Dashboard references sheet 'Machine Drilldown' which has no visual representation in the workbook.`
  - `Dashboard references sheet 'Machine Drill Sheet' which has no visual representation in the workbook.`
  - `Dashboard references sheet 'Machine Drill Summary' which has no visual representation in the workbook.`
  - `Dashboard references sheet 'Executive Overview' which has no visual representation in the workbook.`

### Affected Workbooks (Timeline)
| Date | Workbook | Sheet Referenced | Result |
|------|----------|------------------|--------|
| 2026-10-11 | `ODYN_CEO_Dashboard_full_native_draft_schema_fixed.twbx` | Machine Drilldown | FAIL |
| 2026-10-11 | `ODYN_CEO_Dashboard_full_native_draft_schema_fixed_v2.twbx` | Machine Drill Sheet | FAIL |
| 2026-10-11 | `ODYN_CEO_Dashboard_full_native.twbx` (machine rebuild) | Machine Drill Summary | FAIL |
| 2026-10-11 | `with_executive_dashboard.twbx` | Executive Overview | FAIL (initially worked, then failed on retry) |
| 2026-10-11 | `minimal_drilldown_only.twbx` | Machine Drill Summary | FAIL |

### Unsuccessful Approaches
1. **Renaming worksheets** (Machine Drilldown → Machine Drill Sheet → Machine Drill Summary) — no effect
2. **Cloning working worksheet XML structure** (Job Drilldown → Machine Drill Summary) — no effect
3. **Removing all other worksheets/dashboards** to isolate — minimal drilldown-only still fails
4. **Rebuilding dashboard zones from scratch** — no effect
5. **Regenerating simple-id UUIDs** — no effect
6. **Using different datasource naming** — no effect
7. **Removing devicelayouts, manual-sort, shelf-sorts** (fixed D2E8DA72 but not 2805CF18) — partial progress

### Successful Baseline
- `machine_sheet_only_test.twb` (single worksheet, no dashboard) — **OPENS**
- `tmp_job_only.twbx` (single Job Drilldown worksheet + dashboard) — **OPENS**
- `tmp_machine_dashboard_test.twbx` (single Machine Drill Sheet worksheet + custom dashboard) — **OPENS**

### Suspected Root Causes (Investigation Priority)
1. **Dashboard-to-worksheet reference resolution failure** — Tableau cannot link the dashboard zone's `name` attribute to a valid worksheet visual model, even when both exist in XML
2. **Worksheet visual model not generated** — Worksheet XML exists but Tableau's internal visual representation (pane/encoding/layout cache) is not being built for sheets referenced in dashboards
3. **Datasource dependency mismatch** — Dashboard references datasources that don't match worksheet's active datasource
4. **Workbook identifier collision** — Duplicate simple-ids or datasource names confusing Tableau's internal resolver
5. **XML namespace/schema version mismatch** — Workbook version attributes not compatible with Tableau 2026.2 expectations
6. **Transient Tableau Desktop state** — Previous session caches interfering with fresh loads

### Reproduction Procedure
1. Create a `.twbx` with:
   - At least one worksheet with valid pane/encodings
   - One dashboard with a zone referencing that worksheet by name
   - Matching datasources in both worksheet and dashboard
2. Open in Tableau Desktop 2026.2 (Apple Silicon)
3. Observe `2805CF18` error on load

### Validation Procedure (Automated)
After every workbook build:
```bash
# 1. Kill existing Tableau processes
pkill -f "Tableau Desktop"; sleep 3

# 2. Open workbook and capture logs
L0=$(wc -l < ~/Documents/My\ Tableau\ Repository/Logs/log.txt)
open -a "Tableau Desktop (Apple silicon) 2026.2.app" "workbook.twbx"
sleep 15
L1=$(wc -l < ~/Documents/My\ Tableau\ Repository/Logs/log.txt)
sed -n "$((L0+1)),$L1 p" ~/Documents/My\ Tableau\ Repository/Logs/log.txt | grep -E "2805cf18|no visual representation|Processing FileOpen.*MainWindow is ready"

# 3. PASS if: "Processing FileOpen event. MainWindow is ready" appears WITHOUT 2805CF18
# 4. FAIL if: 2805CF18 appears or "MainWindow is not ready" followed by error dialog
```

### Resolution Status
- **Status:** BLOCKED — Root cause not identified
- **Blocker:** Cannot reliably produce a multi-worksheet dashboard that Tableau accepts
- **Next Investigation:** Build single-worksheet dashboard incrementally, validate each addition

---

## Issue: D2E8DA72 — Schema Parse Errors (RESOLVED)
- **Cause:** `manual-sort`, `shelf-sorts`, empty `devicelayouts` elements
- **Fix:** Removed these elements from workbook XML
- **Verified:** Parse error no longer appears in logs
- **Status:** RESOLVED

---
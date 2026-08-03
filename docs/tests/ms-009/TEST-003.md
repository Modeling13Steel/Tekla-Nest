---
id: TEST-003
milestone: ms-009
---
**Vision:** The full CSV error remediation text is always visible in the dialog body, without requiring "Show Details" click.
**What was tested:** `nest_window.py` source contains `setInformativeText` and not `setDetailedText` in `_show_csv_error`.
**Test type:** Static (source code check)
**Execution mode:** `grep -c "setInformativeText" src/tekla_nest/views/nest_window.py`
**Result:** PASS
**Validation:** grep returns 1 (one occurrence).

---
id: TEST-002
milestone: ms-008
---
**Vision:** export_excel() must produce exactly 2 sheets (Summary + Purchase), not a sheet per profile

**What was tested:** Built a minimal NestResult with one profile and one bar; called export_excel(); loaded workbook with openpyxl; asserted len(wb.sheetnames) == 2

**Test type:** Unit (real openpyxl workbook written to tmp_path)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_two_sheets_only -v`

**Result:** PASS

**Validation:** Workbook has exactly 2 sheets; per-profile sheets and standalone site-image sheet removed

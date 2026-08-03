---
id: TEST-004
milestone: ms-008
---
**Vision:** The Summary sheet must contain actual profile data (not just a stats table), confirming the full PDF-mirror layout is written

**What was tested:** Called export_excel() with a result containing profile "HEA240"; iterated all non-None cell values in the Summary sheet; asserted "HEA240" appears at least once

**Test type:** Unit (real openpyxl workbook written to tmp_path)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_summary_has_profile_data -v`

**Result:** PASS

**Validation:** "HEA240" found in Summary sheet cell values (profile header row)

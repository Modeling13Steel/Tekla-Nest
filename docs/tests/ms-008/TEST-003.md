---
id: TEST-003
milestone: ms-008
---
**Vision:** Sheet names must follow the Summary / Purchase naming convention in any supported language

**What was tested:** Called export_excel() with minimal result; loaded workbook; checked sheetnames[0] starts with a known Summary variant and sheetnames[1] starts with a known Purchase variant (English and Portuguese accepted)

**Test type:** Unit (real openpyxl workbook written to tmp_path)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_sheet_names -v`

**Result:** PASS

**Validation:** Sheet 0 matches "Resumo" (Portuguese), Sheet 1 matches "Compra" or equivalent

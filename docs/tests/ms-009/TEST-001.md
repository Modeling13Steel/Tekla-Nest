---
id: TEST-001
milestone: ms-009
---
**Vision:** The user sees "Close the file in Excel" instead of a raw PermissionError traceback when exporting to a locked file.
**What was tested:** `export_excel()` raises `RuntimeError` with message containing "Close" when `wb.save()` raises `PermissionError`.
**Test type:** Unit (real — monkey-patches `wb.save`)
**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_excel_permission_error -v`
**Result:** PASS
**Validation:** RuntimeError raised; message contains "Close" and the filename.

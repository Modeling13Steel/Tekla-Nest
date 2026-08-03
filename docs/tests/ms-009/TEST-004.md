---
id: TEST-004
milestone: ms-009
---
**Vision:** When a well-formed CSV loads but contains no valid rows, the user sees an informational status message rather than silent success.
**What was tested:** `load_parts_from_csv()` emits `notice` signal when CSV returns empty list.
**Test type:** Unit (mock — patches load_parts_csv to return [])
**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_empty_parts_csv_notice -v`
**Result:** PASS
**Validation:** notice signal captured; message contains "0 peças" or "0 parts".

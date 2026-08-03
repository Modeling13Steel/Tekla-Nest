---
id: TEST-005
milestone: ms-009
---
**Vision:** When a stock CSV loads but contains no valid rows, the user sees a status message.
**What was tested:** `load_client_stock_csv()` emits `notice` signal when CSV returns empty list.
**Test type:** Unit (mock — patches load_stock_csv to return [])
**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_empty_stock_csv_notice -v`
**Result:** PASS
**Validation:** notice signal captured; message contains "0 entradas" or "0 stock".

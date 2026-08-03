# Tests: ms-009 — UX Error Fixes

| ID | What was tested | Test type | Mode | Result | Command |
|---|---|---|---|---|---|
| TEST-001 | Excel PermissionError wraps as RuntimeError with "Close" message | Unit | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_excel_permission_error -v` |
| TEST-002 | config.yaml logo entries point to logo_outline.png | Static | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_config_logo_path -v` |
| TEST-003 | CSV error dialog uses setInformativeText (always visible) | Unit | Static | PASS | `grep -c "setInformativeText" src/tekla_nest/views/nest_window.py` |
| TEST-004 | Empty parts CSV emits notice signal | Unit | Mock | PASS | `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_empty_parts_csv_notice -v` |
| TEST-005 | Empty stock CSV emits notice signal | Unit | Mock | PASS | `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_empty_stock_csv_notice -v` |

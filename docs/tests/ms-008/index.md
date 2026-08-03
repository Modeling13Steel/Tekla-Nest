# Tests: ms-008 — Logo Fix, Pillow Dep, Excel 2-Sheet Rework

| ID | What was tested | Test type | Mode | Result | Command |
|---|---|---|---|---|---|
| TEST-001 | config.yaml logo path exists on disk | Integration | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_config_logo_path_exists -v` |
| TEST-002 | export_excel produces exactly 2 sheets | Unit | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_two_sheets_only -v` |
| TEST-003 | Excel sheet names match Summary/Purchase variants | Unit | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_sheet_names -v` |
| TEST-004 | Summary sheet contains profile name | Unit | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_excel_summary_has_profile_data -v` |
| TEST-005 | Pillow listed in pyproject.toml dependencies | Static | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_pillow_in_dependencies -v` |

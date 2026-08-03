---
id: TEST-002
milestone: ms-009
---
**Vision:** config.yaml logo path is restored to what the user specified.
**What was tested:** Both `app.logo` and `report.logo` entries in config.yaml equal `"resources/logo_outline.png"`.
**Test type:** Static (file content check)
**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms009_ux_errors.py::test_config_logo_path -v`
**Result:** PASS
**Validation:** YAML parsed; both values match expected string.

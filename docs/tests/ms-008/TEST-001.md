---
id: TEST-001
milestone: ms-008
---
**Vision:** config.yaml must point to a logo file that actually exists so the app and PDF report can display it

**What was tested:** get_config() loads the live config.yaml; assert cfg.report_logo_path.exists() is True

**Test type:** Integration (real file system)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_config_logo_path_exists -v`

**Result:** PASS

**Validation:** report_logo_path resolves to resources/logo_original_modern.svg which exists on disk

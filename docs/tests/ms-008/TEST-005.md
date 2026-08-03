---
id: TEST-005
milestone: ms-008
---
**Vision:** Pillow must be declared as a project dependency so openpyxl image embedding works in all environments

**What was tested:** Read pyproject.toml as text; asserted "Pillow" appears in the content

**Test type:** Static (file content check)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms008_logo_excel.py::test_pillow_in_dependencies -v`

**Result:** PASS

**Validation:** "Pillow>=9.0" found in the dependencies array of pyproject.toml

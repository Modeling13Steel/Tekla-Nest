# Tests: ms-007 — Auto-stock Signal Fix + Material Scoping

| ID | What was tested | Test type | Mode | Result | Command |
|---|---|---|---|---|---|
| TEST-001 | auto_populate_stock replace semantics | Unit | Mock | PASS | `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestReplaceSemantics -v` |
| TEST-002 | auto_populate_stock material scoping | Unit | Mock | PASS | `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestMaterialScoping -v` |
| TEST-003 | generate_default_stock pairs API | Unit | Real | PASS | `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestGeneratePairs -v` |
| TEST-004 | over-length bar seeding preserved | Unit | Mock | PASS | `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestOverlengthSeeding -v` |

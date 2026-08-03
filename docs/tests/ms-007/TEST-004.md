---
id: TEST-004
milestone: ms-007
---
**Vision:** A part longer than the longest standard stock bar must trigger an over-length bar; a short part must not

**What was tested:** auto_populate_stock() with a 17000mm part (standard max 12100mm in mock config); assert emitted list contains a bar >= 17000mm. Also tested that a 3000mm part does not generate bars above 12100mm.

**Test type:** Unit (mock)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestOverlengthSeeding -v`

**Result:** PASS

**Validation:** over-length bar with length >= 17000 present for 17000mm part; no bar above 12100mm for 3000mm part

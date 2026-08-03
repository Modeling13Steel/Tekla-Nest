---
id: TEST-003
milestone: ms-007
---
**Vision:** generate_default_stock with (profile, material) pairs produces entries only for the pairs given — no extra materials

**What was tested:** generate_default_stock([("HEB200", "S355JR"), ("IPE300", "S275JR")]); assert correct entries exist and no S235JR entries

**Test type:** Unit (real config via mock)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestGeneratePairs -v`

**Result:** PASS

**Validation:** at least one entry with profile="HEB200"/material="S355JR"; at least one with profile="IPE300"/material="S275JR"; zero S235JR entries

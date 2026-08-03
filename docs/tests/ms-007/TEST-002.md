---
id: TEST-002
milestone: ms-007
---
**Vision:** Auto-stock seeded from parts that all use S355JR must contain only S355JR entries — no S235JR or S275JR

**What was tested:** NestPresenter.auto_populate_stock() with two parts both in S355JR; assert emitted entries contain only S355JR material

**Test type:** Unit (mock)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestMaterialScoping -v`

**Result:** PASS

**Validation:** materials set in emitted stock equals {"S355JR"}; S235JR and S275JR are absent

---
id: TEST-001
milestone: ms-007
---
**Vision:** auto_populate_stock called twice must produce the same market stock entries as calling it once

**What was tested:** NestPresenter.auto_populate_stock() called twice with same parts; assert stock count matches single call and stock_loaded signal is not emitted

**Test type:** Unit (mock)

**Execution mode:** `PYTHONPATH=src python -m pytest tests/test_ms007_autostock.py::TestReplaceSemantics -v`

**Result:** PASS

**Validation:** market_stock_replaced signal emitted with same entries on second call; stock_loaded NOT emitted by auto_populate_stock

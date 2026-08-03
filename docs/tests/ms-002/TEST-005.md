# TEST-005 — Grand total label reflects only data rows

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-5 — The total label counts bars and linear metres from `PurchaseRow`
objects only; `_SubtotalRow` objects are not double-counted.

## Preconditions

- One profile "HEA240": bars 2 × 6000 mm + 1 × 12000 mm.
  - Total bars = 3; total linear m = (2*6000 + 12000)/1000 = 24.00 m.

## Steps

1. Call `widget.set_result(result)`.
2. Read `widget._total_label.text()`.

## Expected Result

- Label contains `"3"` (bar count).
- Label contains `"24.00"` (linear metres).
- Label does NOT contain double-counted values from subtotal rows.

## Automated test

`tests/unit/test_purchase_table.py` — `test_widget_set_result_populates_rows`
asserts both `"3"` and `"24.00"` appear in the total label text.

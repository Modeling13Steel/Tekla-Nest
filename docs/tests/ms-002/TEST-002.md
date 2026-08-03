# TEST-002 — Data rows show linear_m formatted to 2 decimal places

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-2 — Each data row in column 5 shows `(length * count / 1000)` to 2 dp.

## Preconditions

- One profile "HEA240" with bars: 2 × 6000 mm, 1 × 12000 mm.

## Steps

1. Call `widget.set_result(result)`.
2. Find a data row (non-bold) and read cell at column 5.

## Expected Result

- Row with length=6000, count=2: cell text is `"12.00"` (6000*2/1000).
- Row with length=12000, count=1: cell text is `"12.00"` (12000*1/1000).

## Automated test

`tests/unit/test_bar_aggregation.py` — `test_purchase_row_linear_m` verifies
`PurchaseRow.linear_m` property. Widget rendering is exercised through
`test_widget_set_result_populates_rows`.

# TEST-003 — Per-profile subtotal rows are inserted

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-3 — After the last data row for each profile a subtotal row appears
with aggregated count and linear_m and em-dashes in material/length/source columns.

## Preconditions

- Two profiles: "HEA240" (2 rows), "IPE200" (1 row).

## Steps

1. Call `widget.set_result(result)`.
2. Read `widget._table.rowCount()`.
3. Inspect the rows that are _SubtotalRow instances.

## Expected Result

- `rowCount()` equals `5` (3 data + 2 subtotal rows).
- `widget.rows()` still returns only the 3 `PurchaseRow` objects.
- Each subtotal row col 1, 2, 3 shows "—".

## Automated test

`tests/unit/test_purchase_table.py` — `test_widget_set_result_populates_rows`
(single-profile: 2+1=3 rows), plus `_build_display_rows` logic tested via
the multi-profile scenario in the widget test suite.

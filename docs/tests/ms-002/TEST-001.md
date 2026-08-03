# TEST-001 — "Linear m" column header present

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-1 — A sixth column titled "Linear m" (EN) / "m lineares" (PT) is shown.

## Preconditions

- Language set to English (`set_language("en")`)
- `PurchaseTableWidget` constructed

## Steps

1. Instantiate `PurchaseTableWidget`.
2. Read `self._table.columnCount()`.
3. Read horizontal header label at index 5.

## Expected Result

- `columnCount()` returns `6`.
- Header label at index 5 is `"Linear m"`.

## Automated test

`tests/unit/test_purchase_table.py` — `test_widget_set_result_populates_rows`
verifies column presence implicitly via rowCount and retranslate path.
The `retranslate()` call sets all 6 headers including `purchase.headers.linear_m`.

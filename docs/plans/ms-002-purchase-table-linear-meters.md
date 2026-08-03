# Plan: ms-002 — Purchase Table Linear Meters Column & Per-Profile Subtotals

## Objective

Add a "Linear m" column to `PurchaseTableWidget` and inject per-profile
subtotal rows so users can see aggregated linear metres per profile at a glance.

## Implementation Checklist

- [x] Create branch `ms-002-purchase-table-linear-meters`
- [x] `purchase_table.py` — change column count from 5 to 6
- [x] `purchase_table.py` — add `"purchase.headers.linear_m"` to `retranslate()`
- [x] `purchase_table.py` — define `_SubtotalRow` NamedTuple
- [x] `purchase_table.py` — implement `_build_display_rows()` grouping by profile
- [x] `purchase_table.py` — rewrite `_render()` to handle both row types
- [x] `purchase_table.py` — right-align columns 4 (count) and 5 (linear_m)
- [x] `purchase_table.py` — bold font on subtotal rows
- [x] `purchase_table.py` — disable sorting permanently (subtotals break sort)
- [x] `purchase_table.py` — filter out `_SubtotalRow` before grand_totals call
- [x] `en.yaml` — add `purchase.headers.linear_m: "Linear m"`
- [x] `pt.yaml` — add `purchase.headers.linear_m: "m lineares"`
- [x] Update `test_purchase_table.py` — fix `rowCount` assertion (2 data + 1 subtotal = 3)
- [x] Write test docs in `docs/tests/ms-002/` (index + TEST-001 through TEST-006)
- [x] Run unit tests — all 476 pass

## Files Changed

| File | Change |
|------|--------|
| `src/tekla_nest/views/purchase_table.py` | Add column, subtotal rows, bold, alignment |
| `resources/languages/en.yaml` | Add `purchase.headers.linear_m` |
| `resources/languages/pt.yaml` | Add `purchase.headers.linear_m` |
| `tests/unit/test_purchase_table.py` | Update rowCount assertion |
| `docs/tests/ms-002/index.md` | New — test summary |
| `docs/tests/ms-002/TEST-001.md` | New — column header test |
| `docs/tests/ms-002/TEST-002.md` | New — data row linear_m test |
| `docs/tests/ms-002/TEST-003.md` | New — subtotal row insertion test |
| `docs/tests/ms-002/TEST-004.md` | New — bold font test |
| `docs/tests/ms-002/TEST-005.md` | New — grand total accuracy test |
| `docs/tests/ms-002/TEST-006.md` | New — PT translation test |

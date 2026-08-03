# TEST-006 — Regression: Existing Purchase Export Unchanged

**Milestone:** ms-004
**AC:** All pre-existing `test_purchase_export.py` tests continue to pass unchanged.

## Steps

1. Run: `pytest tests/unit/test_purchase_export.py -q`
2. Confirm all 10 tests pass with zero failures.

## Expected

```
10 passed in <t>s
```

Tests covered:
- `test_excel_has_purchase_sheet`
- `test_excel_purchase_sheet_aggregates_by_profile_material_length`
- `test_excel_purchase_sheet_includes_per_profile_subtotals`
- `test_excel_purchase_sheet_grand_total_matches_sum_of_bars`
- `test_csv_contains_purchase_section`
- `test_csv_purchase_section_has_correct_aggregation`
- `test_excel_per_material_sheets_do_not_collide`

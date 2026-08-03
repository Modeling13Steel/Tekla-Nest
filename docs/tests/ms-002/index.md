# ms-002 Test Index — Purchase Table Linear Meters

## Summary

| Test ID | Acceptance Criterion | Description | Status |
|---------|----------------------|-------------|--------|
| TEST-001 | AC-1 | Sixth "Linear m" column header appears in the table | Automated |
| TEST-002 | AC-2 | Each data row shows linear_m (length × count / 1000) formatted to 2 dp | Automated |
| TEST-003 | AC-3 | Per-profile subtotal row is inserted after each profile group | Automated |
| TEST-004 | AC-4 | Subtotal row cells are rendered in bold | Automated |
| TEST-005 | AC-5 | Grand total label is unaffected by subtotal rows (counts only data rows) | Automated |
| TEST-006 | AC-6 | Portuguese translation renders "m lineares" as the column header | Automated |

## Coverage

All acceptance criteria are covered by automated unit tests in
`tests/unit/test_purchase_table.py` and `tests/unit/test_bar_aggregation.py`.
Functional smoke is provided by `tests/functional/test_f19_purchase_tab.py`.

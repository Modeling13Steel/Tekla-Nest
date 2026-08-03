# ms-004 — Excel/PDF Parity: Test Summary

| ID | Title | Status |
|----|-------|--------|
| TEST-001 | Logo on Summary sheet | PASS |
| TEST-002 | KPI row on Summary sheet | PASS |
| TEST-003 | Operator-prep row per profile sheet | PASS |
| TEST-004 | Visual bar strip per bar row | PASS |
| TEST-005 | Site image sheet | PASS |
| TEST-006 | Regression — existing purchase export unchanged | PASS |

All tests verified via automated unit suite (`tests/unit/test_purchase_export.py`)
and manual smoke test against `_multi_material_result()` fixture.

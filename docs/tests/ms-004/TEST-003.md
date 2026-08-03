# TEST-003 — Operator-Prep Row per Profile Sheet

**Milestone:** ms-004
**AC:** Each profile sheet contains an operator-prep summary row at row 1, merged across all columns.

## Steps

1. Call `export_excel(result, path)` with a multi-bar result.
2. Open a profile sheet (e.g., `HEA240_S235JR`).
3. Read cell A1 — expect a string starting with "Prep:".
4. Confirm columns A:N are merged in row 1.
5. Confirm column headers appear at row 2.
6. Confirm data rows start at row 3.

## Expected

- Row 1: merged prep text such as `Prep: 2x 6000mm | Total: 2 bars · 12.00 m`
- Row 2: column header row (bold, primary-colour fill)
- Row 3+: bar data rows interleaved with strip rows

# TEST-004 — Visual Bar Strip per Bar Row

**Milestone:** ms-004
**AC:** After each data row in a profile sheet, a 12pt-high colour-strip row is inserted showing cuts (coloured) and waste (grey).

## Steps

1. Call `export_excel(result, path)` with a bar containing at least 2 cuts.
2. Open the profile sheet.
3. After the first data row (row 3), inspect row 4:
   - Row height = 12.
   - At least one cell has a non-grey `PatternFill`.
   - At least one cell has fill `CCCCCC` (waste grey).
4. Confirm data continues at row 5 (next bar's data row).

## Expected

- Odd rows (3, 5, 7, …): bar data.
- Even rows (4, 6, 8, …): colour strip.
- Strip fills proportional to cuts / original_length.
- Remaining span after cuts filled grey (`CCCCCC`).

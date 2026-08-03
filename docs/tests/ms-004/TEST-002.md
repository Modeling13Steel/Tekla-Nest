# TEST-002 — KPI Row on Summary Sheet

**Milestone:** ms-004
**AC:** Overall Waste %, Total Bars, and Unfit Pieces KPI rows appear on the Summary sheet after the profile data.

## Steps

1. Produce `NestResult` with known profiles and unfit pieces.
2. Call `export_excel(result, path)`.
3. Load workbook; locate Summary sheet.
4. Scan rows below the TOTAL row for KPI labels.

## Expected

| Column A | Column B |
|----------|----------|
| Overall Waste % | `<float>` |
| Total Bars | `<int>` |
| Unfit Pieces | `<int>` |

All label cells have `Font(bold=True)`.

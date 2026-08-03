# TEST-002 — Modal shown for malformed CSV (missing columns)

**Feature:** ms-005 CSV error display  
**Area:** load_parts_from_csv  
**AC:** AC-1 — CsvError triggers csv_error_occurred signal → modal dialog

## Preconditions
- A CSV file exists that is missing required columns (e.g. header is `foo,bar`).

## Steps
1. File > Load Parts from CSV...
2. Select the malformed CSV.

## Expected result
- A QMessageBox Warning dialog appears with:
  - Main text: "CSV loading error"
  - Detailed text: "CSV … is missing required columns: …" plus "Fix:" line.
- Status bar shows a brief error notice.

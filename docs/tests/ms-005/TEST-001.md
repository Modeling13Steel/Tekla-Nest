# TEST-001 — Modal shown for missing CSV file

**Feature:** ms-005 CSV error display  
**Area:** load_client_stock_csv  
**AC:** AC-1 — CsvError triggers csv_error_occurred signal → modal dialog

## Preconditions
- Application launched with no stock loaded.

## Steps
1. File > Load Client Stock from CSV...
2. Select a path that does not exist (e.g. `/tmp/does_not_exist.csv`).

## Expected result
- A QMessageBox Warning dialog appears with:
  - Window title: "Error" (en) / "Erro" (pt)
  - Main text: "CSV loading error"
  - Detailed text: full CsvError message including "Fix:" remediation line.
- Status bar shows a brief error notice.

## Notes
- redact() must NOT be called on the CsvError message in this path.

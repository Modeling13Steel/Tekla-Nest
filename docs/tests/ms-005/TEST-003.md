# TEST-003 — Full remediation text visible in detailed area

**Feature:** ms-005 CSV error display  
**Area:** Modal content  
**AC:** AC-2 — detailed text contains the full CsvError message including Fix: line

## Preconditions
- A CSV file with a known error (e.g. missing required column `quantity`).

## Steps
1. Trigger the CSV error (load malformed stock CSV).
2. In the dialog, click "Show Details..." to expand the detailed text area.

## Expected result
- The detailed text area contains the full CsvError string, including any
  "Fix:" remediation line such as:
  "Fix: Add a 'quantity' column to the CSV file."
- Text is NOT redacted (file paths visible if included).

# TEST-004 — Copy to clipboard button transfers full text

**Feature:** ms-005 CSV error display  
**Area:** Modal interaction  
**AC:** AC-3 — "Copy to clipboard" button copies title + detail to system clipboard

## Preconditions
- Any CSV error has been triggered and the dialog is open.

## Steps
1. In the CSV error dialog, click "Copy to clipboard".
2. Open a text editor and paste (Ctrl+V).

## Expected result
- Pasted text contains the title ("CSV loading error") followed by two
  newlines and the full detailed error text.
- Dialog closes after clicking the button (or OK).

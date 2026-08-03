# TEST-005 — Status bar still updated after CSV error

**Feature:** ms-005 CSV error display  
**Area:** Status bar  
**AC:** AC-4 — error_occurred (status bar) still fires alongside csv_error_occurred

## Preconditions
- Any CSV error condition (missing file or malformed CSV).

## Steps
1. Trigger a CSV load error.
2. Close the modal dialog.
3. Observe the status bar at the bottom of the window.

## Expected result
- The status bar shows a brief error message (operation failed).
- The modal dialog was shown in addition to (not instead of) the status bar update.
- The status bar message is a redacted/translated operation failure string,
  not the full unredacted CsvError text.

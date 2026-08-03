# Spec: ms-005 — CSV Error Display: Modal + Full Remediation

## Purpose
Ensure that when a CSV file fails to load (wrong columns, encoding, bad values), the user sees the full error description and remediation steps in a modal dialog — not just a clipped status-bar message.

## Scope

### In scope
- Route `CsvError` exceptions (from both `load_stock_csv` and `load_parts_csv`) to a modal dialog that displays the full error text including the "Fix:" remediation section.
- Preserve the status-bar notification as a secondary (brief) indicator.
- Update i18n to have a clean short summary key for the status bar and pass the full detail to the modal body.
- Tests confirming modal routing and message completeness.

### Out of scope
- Changing the `CsvError` message text in `csv_loader.py` (already descriptive).
- Changing non-CSV error routing.
- Redesigning the status bar widget.

## Background

`csv_loader.py` already produces detailed `CsvError` messages, e.g.:

```
CSV 'stock.csv' is missing required columns: ['quantidade']
  Found columns: ['qty', 'length', 'perfil']
  Expected (case-insensitive): ['quantidade', 'comprimento', 'perfil']
```

The problem is the display pipeline:
1. Presenter catches the exception and calls `_fail_operation(operation, f"Failed to load stock CSV: {redact(exc)}")`.
2. `_fail_operation` emits `error_occurred` which calls `_show_error(message)`.
3. `_show_error` calls `tr_error(message)` — which may match a translation prefix and truncate the detail — then shows it only on the status bar (single-line, no modal).

CSV loading errors are user-actionable and blocking (the data was not loaded). They must be shown modally with the full text.

## Functional Requirements

- FR-001: When `load_stock_csv` or `load_parts_csv` raises `CsvError`, a modal dialog must appear showing:
  - A short title: "CSV loading error" (translated).
  - The full `CsvError` message body, including any "Fix:" / remediation lines, rendered in a scrollable text area.
- FR-002: The status bar must simultaneously show a brief summary (e.g. "Failed to load stock CSV — see details above").
- FR-003: The full `CsvError` message must not be truncated by `tr_error()` or `redact()`.
- FR-004: The modal must include a "Copy to clipboard" button so the user can paste the error when asking for support.

## Non-Functional Requirements

- NFR-001: The modal must not block the event loop or prevent the main window from remaining responsive after it is dismissed.
- NFR-002: The existing modal path (`message.startswith("modal:")`) must continue to work for other error types.

## Acceptance Criteria

- AC-001 (FR-001): Given a CSV file with missing column "quantidade", opening it triggers a `QDialog` (or `QMessageBox` with detail text) that contains the text "missing required columns".
- AC-002 (FR-001): The dialog body contains the "Fix:" / "Expected:" remediation line from the original `CsvError`.
- AC-003 (FR-002): The status bar shows a brief error indicator simultaneously with the modal.
- AC-004 (FR-003): The string "required columns" is present verbatim in the dialog text (not replaced by a generic "unknown error" translation).
- AC-005 (FR-004): The dialog has a button labelled "Copy" (or "Copy to clipboard") that writes the full error text to the system clipboard.

## Open Questions

### User standpoint
- Q: Should the dialog be a `QMessageBox` (simple) or a custom `QDialog` with a scrollable `QTextEdit` body?
  - Recommended: `QMessageBox` with `setDetailedText()` — shows a "Details…" expander with the full multiline message. Simple to implement, consistent with OS conventions.
- Q: Should "Copy to clipboard" be in the main button row or inside the detail expander?
  - Assumed: standard `QMessageBox` buttons row, only if we use a custom dialog. For `setDetailedText`, the native "Copy" comes from the OS text selection in the detail area.

### Engineer standpoint
- Q: Where should the modal logic live — presenter or view?
  - The presenter currently emits `error_occurred(message: str)`. The cleanest approach: add a separate signal `csv_error_occurred(title: str, detail: str)` emitted specifically for `CsvError`, and connect it to a dedicated dialog in `nest_window.py`. This avoids coupling `CsvError` specifics to the generic error path.
  - Alternative: prefix message with `"modal:"` in the presenter and extend `_show_error` to render multiline text. Simpler but messier.
  - Recommended: new signal.
- Q: Does `redact()` affect `CsvError` messages?
  - `redact()` only strips license keys and machine IDs (regex patterns). CSV error text won't match those patterns. However, to be safe, the `CsvError` detail should be passed directly without going through `redact()`.

### System standpoint
- Q: Is there a risk of sensitive data in a CSV error message (e.g. file path)?
  - File paths in error messages are acceptable for local desktop apps. No PII involved.

## Related ADRs
None required.

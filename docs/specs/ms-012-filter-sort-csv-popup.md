# Spec: ms-012 — Filter chip sort + CSV error diagnostics

## Purpose
Fix material filter chips appearing in different orders across tabs, and ensure every CSV
load failure shows a modal dialog on all platforms (including Windows) with stdout logging
for diagnostics.

## Scope

### In scope
- Sort material chips alphabetically in both parts and stock filter bars.
- Add stdout logging at application startup so CSV errors appear in the console.
- Add `print()` diagnostics in `_show_csv_error` and the CSV `except` branches.
- Ensure `except Exception` paths in `load_parts_from_csv` and `load_client_stock_csv`
  also emit `csv_error_occurred` (modal dialog) in addition to `_fail_operation`.

### Out of scope
- Sorting chips for any column other than material.
- Changing the log level or adding a log file.
- Investigating the root cause of the Windows dialog suppression beyond stdout diagnostics.
- Re-sorting chips after manual table edits.

## Functional Requirements

- FR-001: Material filter chips in the parts tab must always be ordered
  case-insensitively alphabetically, regardless of row insertion order.
- FR-002: Material filter chips in the stock tab must always be ordered
  case-insensitively alphabetically, matching the parts tab order for common materials.
- FR-003: Any exception during CSV part loading (CsvError or other) must trigger
  the `csv_error_occurred` signal so a modal dialog is shown.
- FR-004: Any exception during CSV stock loading (CsvError or other) must trigger
  the `csv_error_occurred` signal so a modal dialog is shown.
- FR-005: On application startup, a stdout log handler must be configured so that
  WARNING+ messages (including LOGGER.exception tracebacks) appear in the console
  on Windows and macOS.
- FR-006: `_show_csv_error` must print a diagnostic line to stdout before showing
  the dialog, confirming the method was reached.

## Non-Functional Requirements

- NFR-001: The stdout log handler must be a no-op when `sys.stdout` is None
  (windowed / no-console builds on Windows).
- NFR-002: No new public API surface changes to `NestPresenter` or `NestWindow`.

## Acceptance Criteria

- AC-001 (FR-001, FR-002): Given parts with materials ["S355JR", "S235JR"] and stock with
  materials ["S235JR", "S355JR"], when both CSVs are loaded, then both filter bars show
  chips in the order ["S235JR", "S355JR"].
- AC-002 (FR-003): Given a CSV file that raises an unexpected exception during parts load,
  when `load_parts_from_csv` is called, then `csv_error_occurred` is emitted and
  `_fail_operation` is also called.
- AC-003 (FR-004): Same as AC-002 but for `load_client_stock_csv`.
- AC-004 (FR-005): Given `sys.stdout` is not None, after `main()` configures logging, a
  WARNING-level log message appears on stdout.
- AC-005 (FR-006): When `_show_csv_error` is called, a line containing "CSV error dialog"
  is printed to stdout before `box.exec()` runs.

## Open Questions

### User standpoint
- Q: Should the stdout log be removed in a follow-up release once the Windows issue is
  confirmed? **A: Yes — this is a temporary diagnostic measure.**

### Engineer standpoint
- Q: Is the `except Exception` path in the CSV methods ever triggered in practice?
  **A: Unlikely for normal use but kept as a safety net; gap now closed with modal.**

### System standpoint
- Q: Does `logging.basicConfig(force=True)` interfere with any third-party library logging
  already configured? **A: No third-party logging setup is done before `main()`, so safe.**

## Related ADRs
- [ADR-0003](../adr/0003-csv-error-logging-and-modal.md)

# Spec: ms-014 — Close guardrail for unsaved optimization results

## Purpose
Prevent silent data loss: when the user tries to close the app while an optimization result
has not been exported, prompt them to export or confirm the discard.

## Scope

### In scope
- `NestPresenter`: `_result_exported` flag; set/reset logic in calculate, export_pdf,
  export_excel, export_csv; `result_exported` read-only property.
- `NestWindow.closeEvent`: prompt when `has_result and not result_exported`.
- Close guard dialog: "Export PDF...", "Export Excel...", "Close without saving", "Cancel".
  Successful export from the dialog closes the window automatically.
- i18n strings for the new dialog keys.

### Out of scope
- Guarding against unsaved parts/stock (no export format for those).
- A project-file save/load format.
- Prompting when the result was already exported (any format counts as "saved").

## Functional Requirements

- FR-001: When the user attempts to close the window AND `has_result is True` AND
  `result_exported is False`, a modal close guard dialog must appear.
- FR-002: The close guard dialog must offer at least two export actions (PDF, Excel) and a
  "Close without saving" destructive action and a "Cancel" action.
- FR-003: After successfully exporting from the close guard dialog, the window must close.
- FR-004: If the user cancels the file-chooser from the close guard, the window must NOT close.
- FR-005: If the user clicks "Close without saving", the window must close immediately without exporting.
- FR-006: If the user clicks "Cancel" or dismisses the dialog, the window must NOT close.
- FR-007: `result_exported` must be False after a new optimization completes.
- FR-008: `result_exported` must be True after any of export_pdf, export_excel, export_csv
  succeeds.
- FR-009: No close guard dialog must appear when the app is in an empty state
  (`has_result is False`).
- FR-010: No close guard dialog must appear after the result has been exported
  (`result_exported is True`).

## Non-Functional Requirements

- NFR-001: The close guard must not interfere with headless tests that programmatically call
  `window.close()` — tests that need to skip the guard must set `pres._result_exported = True`
  or call the window's `_force_close()` helper.
- NFR-002: `result_exported` is a read-only property on `NestPresenter`; the flag is managed
  entirely by the presenter.

## Acceptance Criteria

- AC-001 (FR-001, FR-009): Given no result, when `closeEvent` fires, then no dialog appears
  and the window closes.
- AC-002 (FR-001): Given a result and `result_exported is False`, when `closeEvent` fires,
  then the close guard dialog appears.
- AC-003 (FR-010): Given a result and `result_exported is True`, when `closeEvent` fires,
  then no dialog appears and the window closes.
- AC-004 (FR-007): After a new optimization run, `result_exported` is False.
- AC-005 (FR-008): After a successful `export_pdf`, `result_exported` is True.
- AC-006 (FR-008): After a successful `export_excel`, `result_exported` is True.
- AC-007 (FR-005): Clicking "Close without saving" in the dialog closes the window.
- AC-008 (FR-006): Clicking "Cancel" in the dialog does not close the window.

## Open Questions

### User standpoint
- Q: Should clicking "Export PDF" in the close guard also close the window if export succeeds?
  **A: Yes — the user's intent is to save then close.**

### Engineer standpoint
- Q: `prompt_export_pdf` returns `True` on success. Can we reuse it here?
  **A: Yes — call it inside `closeEvent`, then accept/ignore the event based on return value.**

### System standpoint
- Q: Does `QCloseEvent` need `event.accept()` explicitly on normal close?
  **A: Yes — `closeEvent` must call `event.accept()` to allow closing and
  `event.ignore()` to prevent it.**

## Related ADRs
- [ADR-0005](../adr/0005-close-guard-unsaved-results.md)

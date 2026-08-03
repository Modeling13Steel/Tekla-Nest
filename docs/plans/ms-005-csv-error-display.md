# Implementation Plan: ms-005 — CSV Error Display

## Branch
`ms-005-csv-error-display` — rebased on `ms-004-excel-pdf-parity`

## Spec
[docs/specs/ms-005-csv-error-display.md](../specs/ms-005-csv-error-display.md)

## Tasks

- [ ] FR-001 / FR-003 — Add `csv_error_occurred = Signal(str, str)` to `NestPresenter` (title, detail); in `load_client_stock_csv()` and `load_parts_csv_from_file()`, catch `CsvError` separately from generic `Exception`: emit `csv_error_occurred(title, str(exc))` (do NOT pass through `redact()`)
- [ ] FR-001 — In `NestWindow.__init__`, connect `self._pres.csv_error_occurred.connect(self._show_csv_error)`
- [ ] FR-001 / FR-004 — Implement `_show_csv_error(title: str, detail: str)` in `nest_window.py`: create a `QMessageBox` with `setText(title)`, `setDetailedText(detail)`, `setIcon(QMessageBox.Icon.Warning)`, add a "Copy" `QPushButton` that writes `f"{title}\n\n{detail}"` to `QApplication.clipboard()`
- [ ] FR-002 — After emitting `csv_error_occurred`, also emit `error_occurred` with the short summary (status bar stays) 
- [ ] FR-003 — Confirm that `redact()` is NOT called on the `CsvError` message in the new path (raw `str(exc)` is used)
- [ ] Add i18n key `errors.csv_load_title` to `en.yaml` and `pt.yaml`
- [ ] Tests written and passing — see `docs/tests/ms-005/`
- [ ] Linters clean
- [ ] Acceptance criteria validated and results recorded in `docs/tests/ms-005/index.md`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | Signal + presenter catch block + `_show_csv_error` dialog + i18n keys | `claude-haiku-4-5-20251001` |
| Test writer | Tests for AC-001 through AC-005 | `claude-haiku-4-5-20251001` |

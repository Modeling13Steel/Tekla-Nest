# Implementation Plan: ms-009 — UX Error Fixes

## Branch
`ms-009-ux-error-fixes` — rebased on `ms-008-logo-excel-rework`

## Spec
[docs/specs/ms-009-ux-error-fixes.md](../specs/ms-009-ux-error-fixes.md)

## Tasks

- [ ] AC-001 — In `excel_report.py`, wrap `wb.save(str(out))` in a try/except catching `PermissionError` and re-raise as `RuntimeError("Cannot save '{out.name}': the file is open in another application.\n  Fix: Close '{out.name}' in Excel (or any other program) and export again.")`
- [ ] AC-002 — In `config.yaml`, revert both logo entries back to `"resources/logo_outline.png"`
- [ ] AC-003 — In `nest_window.py` `_show_csv_error`, change `box.setDetailedText(detail)` to `box.setInformativeText(detail)`
- [ ] AC-004 — In `nest_presenter.py` `load_client_stock_csv`, after `self.stock_loaded.emit(self._client_stock)`, add: if `not self._client_stock: self.notice.emit(tr("status.csv_stock_empty"))`
- [ ] AC-004 — In `nest_presenter.py` `load_parts_from_csv`, after `self.parts_loaded.emit(self._parts)`, add: if `not self._parts: self.notice.emit(tr("status.csv_parts_empty"))`
- [ ] Add i18n keys `status.csv_stock_empty` and `status.csv_parts_empty` to `en.yaml` and `pt.yaml`
- [ ] Tests written and passing — see `docs/tests/ms-009/`
- [ ] Linters clean
- [ ] Acceptance criteria recorded in `docs/tests/ms-009/index.md`
- [ ] `git push -u teklanest ms-009-ux-error-fixes`

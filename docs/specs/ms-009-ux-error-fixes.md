# Spec: ms-009 — UX Error Fixes (Excel Lock, Logo Config, CSV Visibility)

## Purpose
Three user-visible defects reported after ms-008:

1. **Excel PermissionError** — saving an Excel file that is already open in Excel yields an
   unhandled `PermissionError` traceback. User sees a Python crash, not an actionable message.
2. **Logo config reverted** — ms-008 changed `config.yaml` from `logo_outline.png` to
   `logo_original_modern.svg` against user intent. Must be reverted to `logo_outline.png`.
3. **CSV error detail hidden** — `_show_csv_error` uses `QMessageBox.setDetailedText()`,
   which hides the remediation text behind a collapsible "Show Details" button. Users see
   only the terse title and conclude "nothing happened". Additionally, loading a CSV that
   produces 0 valid entries gives no feedback at all.

## Scope

### In scope
- Catch `PermissionError` (and `OSError` with `errno.EACCES`) in `excel_report.py`'s
  `export_excel()` and re-raise as `RuntimeError` with "Close the file in Excel first."
- Revert `config.yaml` both `app.logo` and `report.logo` entries to `"resources/logo_outline.png"`.
- Change `_show_csv_error` in `nest_window.py`: replace `box.setDetailedText(detail)` with
  `box.setInformativeText(detail)` so the full remediation text is always visible.
- Add a notice (status bar) when `load_client_stock_csv` or `load_parts_from_csv` completes
  with 0 entries — so the user knows the file was read but yielded nothing.

### Out of scope
- Creating or replacing the `logo_outline.png` file — the user manages that asset.
- Changing any other UI behaviour.

## Acceptance Criteria

- AC-001: When the user tries to export Excel to a path that Windows has locked, the error
  message contains the text "Close" and names the file — no raw `PermissionError` traceback.
- AC-002: `config.yaml` `app.logo` and `report.logo` both read `"resources/logo_outline.png"`.
- AC-003: When a CSV raises `CsvError`, the QMessageBox body (`informativeText`) contains the
  full remediation string without the user needing to click any expander.
- AC-004: When a CSV loads successfully but yields 0 entries, a status-bar notice informs the
  user ("CSV loaded — 0 entries found. Check that quantidade and comprimento are non-zero.").

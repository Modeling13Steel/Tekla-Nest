# Implementation Plan: ms-008 — Logo Visibility Fix + Excel 2-Sheet Rework

## Branch
`ms-008-logo-excel-rework` — rebased on `ms-007-autostock-signal-fix`

## Spec
[docs/specs/ms-008-logo-excel-rework.md](../specs/ms-008-logo-excel-rework.md)

## Tasks

### Logo fix
- [ ] AC-001 / FR-001 — In `config.yaml`, change both `app.logo` and `report.logo` from `"resources/logo_outline.png"` to `"resources/logo_original_modern.svg"`
- [ ] AC-002 / FR-002 — In `pdf_report.py` `render_report_html()`, add `LOGGER.warning("Logo not found at %s — report will have no logo", report_logo_path)` when `not report_logo_path.exists()`
- [ ] AC-002 — In `excel_report.py`, replace `except Exception: pass` logo block with `LOGGER.warning(...)` for missing file + `except ImportError` for missing openpyxl/Pillow

### Dependency
- [ ] AC-005 / FR-005 — In `pyproject.toml`, add `"Pillow>=9.0"` to the core `dependencies` array

### Excel 2-sheet rework
- [ ] AC-003 / FR-003 — Remove the per-profile sheet creation loop from `export_excel()`
- [ ] AC-003 — Remove the separate "Site Image" sheet creation block
- [ ] AC-004 / FR-004 — Rework the "Summary" sheet to be the full PDF mirror:
  - Keep existing logo placement at A1 (already implemented)
  - Add company name + generated timestamp in header area (row 2)
  - Add KPI hero block: Overall Waste %, Total Bars, Unfit Pieces, Profile Count
  - Add per-profile sections sequentially on the same sheet: each with profile header row (bold, primary fill), prep summary row, data table (# / Bar Mark / Bar Length / Cuts / Cut Marks / Waste [/ Material] [/ Source]), data rows + strip rows, unfit pieces (if any)
  - Embed attached site image at the bottom of the Summary sheet (after all profiles)
- [ ] AC-003 — Keep `_write_purchase_sheet()` call unchanged
- [ ] Tests written and passing — see `docs/tests/ms-008/`
- [ ] Linters clean (`ruff check src/`)
- [ ] Acceptance criteria validated in `docs/tests/ms-008/index.md`
- [ ] `git push -u origin ms-008-logo-excel-rework`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | All code changes above | `claude-sonnet-4-6` |
| Test writer | pytest tests for AC-001 through AC-005 | `claude-haiku-4-5-20251001` |

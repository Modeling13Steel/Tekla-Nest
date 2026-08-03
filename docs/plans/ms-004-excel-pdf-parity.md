# Implementation Plan: ms-004 — Excel Export PDF Structural Parity

## Branch
`ms-004-excel-pdf-parity` — rebased on `ms-003-pdf-logo-size`

## Spec
[docs/specs/ms-004-excel-pdf-parity.md](../specs/ms-004-excel-pdf-parity.md)

## Tasks

- [ ] FR-001 — In `_write_summary_sheet()` (new helper extracted from `export_excel()`), embed logo image using `openpyxl.drawing.image.Image(select_logo_variant(...))`, anchor at A1, set `height=50`, shift header table rows down accordingly
- [ ] FR-002 — Add KPI row to Summary sheet: overall_waste_pct, total bars, unfit count — below profile stats table
- [ ] FR-003 — In each profile sheet, insert operator-prep row 1 as a bold merged cell: `f"Prep: {', '.join(f'{c}× {l:.0f} mm' for l, c in prep.by_length)} | Total: {prep.total_bars} bars · {prep.linear_m:.2f} m"` using `aggregate_prep()` data; shift existing column-header row to row 2 and data to row 3+
- [ ] FR-004 — After each bar data row, insert a "bar strip" row: compute proportional column spans for each cut and the waste; merge cells and apply `PatternFill` — cut colours from `material_palette`, waste `#CCCCCC`; use `ROW_HEIGHT_STRIP = 12` pt
- [ ] FR-005 — Add `_write_site_image_sheet()`: if `attached_image_path` is provided, create a sheet titled `labels.site_image_sheet`, embed image anchored at A1
- [ ] FR-006 — Ensure scope filter (`filter_result`) is applied before any of the above, including the site image sheet (always included if image present, regardless of scope)
- [ ] Update `export_excel()` signature to accept `attached_image_path: str | None = None`; thread it through from presenter (`nest_presenter.export_excel()`)
- [ ] Tests written and passing — see `docs/tests/ms-004/`
- [ ] Linters clean
- [ ] Acceptance criteria validated and results recorded in `docs/tests/ms-004/index.md`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer A | FR-001 + FR-002: logo + KPI in Summary sheet | `claude-sonnet-4-6` |
| Implementer B | FR-003: operator prep row per profile sheet | `claude-haiku-4-5-20251001` |
| Implementer C | FR-004: bar strip coloured cells per bar | `claude-sonnet-4-6` |
| Implementer D | FR-005: site image sheet + signature update | `claude-haiku-4-5-20251001` |
| Test writer | Tests for AC-001 through AC-006 | `claude-haiku-4-5-20251001` |

> Implementers A–D work on separate functions; coordinate merge order: A → B → C → D (D needs the final signature).

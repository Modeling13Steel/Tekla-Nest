# Spec: ms-008 — Logo Visibility Fix + Excel 2-Sheet Rework

## Purpose
Three related issues need to be resolved together:

1. **Logo not visible anywhere** (preview, PDF, Excel) — `config.yaml` points to
   `resources/logo_outline.png` which does not exist; the code silently skips the logo
   with no warning.
2. **Excel image embedding broken** — `openpyxl.drawing.image.Image` requires Pillow to
   read image dimensions; Pillow is not declared as a dependency; the `except Exception: pass`
   block silently swallows the failure.
3. **Excel structure** — should have exactly two sheets: "Summary" (mirrors the PDF report
   layout exactly) and "Purchase" (existing purchase aggregation). Per-profile sheets and
   the standalone site-image sheet must be removed.

## Scope

### In scope
- Fix `config.yaml`: update `app.logo` and `report.logo` to reference `logo_original_modern.svg`
  (which exists in the resources directory).
- Add a `LOGGER.warning` in `pdf_report.py` and `excel_report.py` when the configured logo
  path does not exist, so the failure is visible in logs.
- Add `Pillow>=9.0` to `pyproject.toml` as a core dependency (required by openpyxl for image
  dimension reading; without it, `XlImage` raises `AttributeError` or `ImportError`).
- Replace the `except Exception: pass` logo block in `excel_report.py` with an explicit
  `except ImportError` (openpyxl missing) and a `LOGGER.warning` for missing-file cases.
- Rework `export_excel()` to produce exactly two sheets:
  - **"Summary"** — full structural mirror of the PDF:
    - Logo (top-left) + company name + generated timestamp
    - KPI hero row: Overall Waste %, Total Bars, Unfit Pieces, Profile Count
    - Per-profile sections (one after another, same sheet), each containing:
      - Profile/material header row (bold, primary colour fill)
      - Operator-prep summary row (e.g. "3× 6100mm, 1× 12100mm | 4 bars · 24.4 m")
      - Data table with header: #, Bar Mark, Bar Length, Cuts, Cut Marks, Waste (mm)
      - Data rows + colour strip rows (same colour mapping as per-profile sheets today)
      - Unfit pieces section (if any)
    - Attached site image embedded at the bottom (below all profile sections)
  - **"Purchase"** — existing `_write_purchase_sheet()` logic, unchanged.
- Remove all per-profile sheets and the standalone "Site Image" sheet.

### Out of scope
- Changing the PDF rendering or preview HTML logic.
- Changing the purchase aggregation logic inside `_write_purchase_sheet()`.
- Changing `AppConfig.report_logo_path` default (it already defaults to
  `logo_original_modern.svg`; only `config.yaml` needs fixing).

## Functional Requirements

- FR-001: The logo must be visible in the in-app preview, in exported PDF, and on the
  Summary sheet of exported Excel files when the configured logo file exists.
- FR-002: If the configured logo file does not exist, a `WARNING`-level log line must be
  emitted naming the missing path; the export must continue without the logo (no crash,
  no silent swallow).
- FR-003: Excel export must produce exactly two sheets: "Summary" and "Purchase".
- FR-004: The Excel "Summary" sheet must contain — in order — logo/header, KPI block,
  per-profile sections with data + strip rows, and the attached site image (if any).
- FR-005: Pillow must be listed as a dependency so `openpyxl.drawing.image.Image` can
  read PNG/JPG dimensions reliably.

## Non-Functional Requirements

- NFR-001: The Excel "Summary" sheet must be the active sheet (first) when the workbook
  opens in Excel/LibreOffice.
- NFR-002: No change to CSV export, PDF export, or the preview HTML rendering paths.
- NFR-003: The `_write_purchase_sheet()` function must remain unchanged internally.

## Acceptance Criteria

- AC-001 (FR-001): With `config.yaml` pointing to `logo_original_modern.svg`, the preview
  shows a logo `<img>` tag with non-empty `src`, and the exported PDF contains the logo image.
- AC-002 (FR-002): With `config.yaml` pointing to a non-existent file, the export completes
  and a WARNING log line containing the missing path is emitted.
- AC-003 (FR-003): `wb.sheetnames` returns exactly `["Summary", "Purchase"]` (or localised
  equivalents) after `export_excel()`.
- AC-004 (FR-004): The Summary sheet row 1 is not blank when a valid logo path is configured
  (logo image placed at A1).
- AC-005 (FR-005): `pyproject.toml` lists `Pillow>=9.0` (or `pillow>=9.0`) in the core
  dependencies array.

## Open Questions

### User standpoint
- Q: Should the Summary sheet use the same column structure as the per-profile sheets today
  (8 columns: #, Bar Mark, Bar Length, Cuts, Cut Marks, Waste, Material, Source)?
  A: Yes, mirror the PDF which includes all columns controlled by `show_material`
  and `show_stock_source` config flags.

### Engineer standpoint
- Q: Does openpyxl require Pillow for SVG logos?
  A: No — openpyxl only calls Pillow for raster images (PNG/JPG). SVG logos are not
  supported by openpyxl at all; use the PNG fallback. `select_logo_variant()` already
  handles variant selection; `excel_report.py` already filters to
  `.png/.jpg/.jpeg/.bmp/.gif` extensions. No change needed here.

### System standpoint
- Q: Will removing per-profile sheets break any tests?
  A: Tests for ms-004 assert per-profile sheets exist. Those tests must be updated to
  assert the new 2-sheet structure.

## Related ADRs
- None required (configuration fix + structural rework with no new architectural patterns).

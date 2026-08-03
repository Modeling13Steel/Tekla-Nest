# Spec: ms-004 — Excel Export: PDF Structural Parity

## Purpose
Bring the Excel export to structural parity with the PDF report by adding: a branded logo header on the Summary sheet, operator-prep summary rows on each profile sheet, a visual bar-cutting strip per bar, and the attached site image in a dedicated sheet.

## Scope

### In scope
1. **Logo** — embed the report logo image at the top-left of the Summary sheet header area.
2. **KPI summary row** — add overall waste %, total bars, and unfit count below the logo in the Summary sheet (mirroring the PDF KPI hero).
3. **Operator prep row** — insert a formatted text row at the top of each profile sheet showing `N× Lmm` counts (matching the PDF prep-header chips).
4. **Visual bar strip** — for each bar row on a profile sheet, add a secondary row of coloured merged cells representing the cuts proportionally (each cut segment a distinct colour; waste/scrap in a neutral grey).
5. **Attached site image** — if an image is attached, embed it in a new "Site Image" sheet at the end of the workbook.
6. Regression tests confirming the new sheets and cells are present.

### Out of scope
- Interactive Excel charts or pivot tables.
- Changing the PDF, CSV, or in-app report rendering.
- Embedding the visual bar strip in the Purchase sheet.
- Changing the column layout of existing sheets.

## Functional Requirements

- FR-001: The Summary sheet must contain an embedded logo image anchored at cell A1, sized to approximately 50 pt tall (proportional width).
- FR-002: The Summary sheet must include a KPI row showing: overall waste %, total bars used, total unfit pieces.
- FR-003: Each profile sheet must begin with an operator-prep row (row 1) formatted as bold text: `"Prep: N× L mm, N× L mm … | Total: X bars · Y.YY m"`, before the column-header row.
- FR-004: Each bar data row must be immediately followed by a "bar strip" row — a set of merged cells coloured to represent each cut segment and the remaining waste, proportional to the bar length. The strip row spans the same columns as the data section. Each cut uses a colour from the design-system material palette; waste is `#CCCCCC`.
- FR-005: If an attached site image is provided, a sheet named "Site Image" must be appended last in the workbook, containing the image anchored at A1.
- FR-006: All new content must respect the `scope` filter — only the selected profiles appear.

## Non-Functional Requirements

- NFR-001: Excel file size must not exceed 3× the current baseline for a typical 50-bar result with a JPEG site image.
- NFR-002: Export time must not exceed 5 seconds for a typical 50-bar result.
- NFR-003: The workbook must open without errors in Microsoft Excel 365, LibreOffice Calc, and Google Sheets. (Logo and bar strips may render differently in Google Sheets — this is acceptable.)

## Acceptance Criteria

- AC-001 (FR-001): The exported workbook contains an `XlsxWriter`/`openpyxl` image object anchored at `Summary!A1` with height ≤ 50 pt.
- AC-002 (FR-002): The Summary sheet contains cells with values equal to `result.overall_waste_pct`, total bar count, and unfit piece count.
- AC-003 (FR-003): Row 1 of each profile sheet contains a merged cell with text matching `"Prep: …"`.
- AC-004 (FR-004): For a result with one HEA200 bar containing cuts [2000, 3000] on a 6000 mm bar, row 3 of the HEA200 sheet contains filled cells: two coloured cut cells and one grey waste cell, each merged proportionally (2/6, 3/6, 1/6 of the strip width respectively).
- AC-005 (FR-005): Given an attached JPEG image, the workbook contains a sheet named "Site Image" with an embedded image object at A1.
- AC-006 (FR-006): When scope filters to one profile, only that profile's sheet is present; "Site Image" (if applicable) and "Summary"/"Purchase" are always present.

## Open Questions

### User standpoint
- Q: Should the bar strip row height be fixed (e.g. 12 pt) or taller for visibility?
  - Assumed: 12 pt (double a normal row), sufficient for colour recognition without inflating the file.
- Q: Should cut colours cycle through the material palette or use a fixed set?
  - Assumed: cycle through the material palette (same colours as the in-app preview).
- Q: Should the "Site Image" sheet use the actual file name as the sheet title?
  - Assumed: fixed name "Site Image" (translated via i18n) for predictability.

### Engineer standpoint
- Q: `openpyxl`'s `add_image()` requires a file path or `PIL.Image` — for the logo, the path is available via `select_logo_variant()`. For the attached image, the `attached_image_path` is available from the presenter. No base64 decoding needed.
- Q: Bar strip proportional widths: each cut segment occupies `round(cut_length / bar_length * N_COLS)` columns, where `N_COLS` is the number of data columns. Rounding error at the last segment must be absorbed by the waste cell.
- Q: `openpyxl` merged cells and `add_image` are independent operations — the strip row uses `merge_cells()` with `PatternFill`. This is well-supported.
- Q: Does the bar strip row break sort operations on profile sheets?
  - Sort is not enabled on profile sheets. Non-issue.

### System standpoint
- Q: Does embedding multiple images significantly increase file size?
  - For typical logo PNG (< 100 KB) + JPEG site image (< 2 MB) + SVG-rasterised cuts (none — cuts are cell fills, not images), the overhead is acceptable.
- Q: Are there openpyxl version constraints?
  - `add_image` requires `openpyxl >= 2.5`. The project already uses openpyxl for the existing export; no version bump expected.

## Related ADRs
None required — all implementation choices follow established patterns in `excel_report.py`.

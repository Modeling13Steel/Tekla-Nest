# TEST-001 — Logo on Summary Sheet

**Milestone:** ms-004
**AC:** Logo image inserted at A1 on the Summary sheet; data rows offset by 4 rows.

## Steps

1. Run `export_excel(result, path)` with a valid `report_logo_path` in config.
2. Open the resulting `.xlsx` in Excel or `load_workbook`.
3. Inspect `ws_summary._images` — expect at least one `Image` anchored at `A1`.
4. Confirm column headers appear at row 5 (not row 1).

## Expected

- Logo image present at A1.
- Headers at row 5, profile data from row 6 onward.
- If logo path does not exist or is not a raster format, export succeeds without image (graceful degradation).

## Notes

- SVG logos are skipped silently (openpyxl does not support SVG).
- PNG/JPG/BMP/GIF logos are inserted.

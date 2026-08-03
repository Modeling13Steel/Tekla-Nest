# TEST-005 — Site Image Sheet

**Milestone:** ms-004
**AC:** When `attached_image_path` is provided and the file exists, a "Site Image" sheet is added as the last sheet with the image anchored at A1 (600×400px).

## Steps

1. Create a temporary PNG file.
2. Call `export_excel(result, path, attached_image_path=tmp_png)`.
3. Load workbook; confirm `"Site Image"` is in `wb.sheetnames`.
4. Inspect `ws_img._images` — expect one `Image` at anchor `A1`.
5. Re-run without `attached_image_path` — confirm "Site Image" sheet is absent.

## Expected

- Sheet title = `"Site Image"` (EN) / `"Imagem do Local"` (PT).
- Image anchored at A1, height=400, width=600.
- No sheet created if `attached_image_path=None` or file does not exist.

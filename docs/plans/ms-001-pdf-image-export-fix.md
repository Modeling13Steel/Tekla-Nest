# Plan ms-001: PDF Image Export Fix

**Status:** In Progress
**Date:** 2026-06-08

## Steps

- [x] Read and understand `export_pdf` in `nest_presenter.py`
- [x] Define `_DataUriTextDocument(QTextDocument)` with `loadResource()` override
- [x] Replace `doc = QTextDocument()` with `doc = _DataUriTextDocument()`
- [x] Write ADR (`docs/archive/adr/0001-pdf-image-qtextdocument.md`)
- [x] Write spec (`docs/specs/ms-001-pdf-image-export-fix.md`)
- [x] Write test index (`docs/tests/ms-001/index.md`)
- [x] Write TEST-001 (`docs/tests/ms-001/TEST-001-html-contains-image.md`)
- [x] Write TEST-002 (`docs/tests/ms-001/TEST-002-no-image-no-regression.md`)
- [x] Run full test suite and verify no regressions
- [x] Commit on branch `ms-001-pdf-image-export-fix`

## Notes

- `_DataUriTextDocument` is defined as a private nested class inside `export_pdf` to keep it co-located with its only use site.
- No changes to `pdf_report.py` or `report_template.html`.
- PySide6 does not require wrapping the returned `QImage` in `QVariant`.

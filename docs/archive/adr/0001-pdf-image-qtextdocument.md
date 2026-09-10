# ADR 0001: PDF Image Export via QTextDocument Subclass

**Date:** 2026-06-08
**Status:** Accepted

## Context

`export_pdf` in `NestPresenter` uses `QTextDocument.setHtml()` followed by `doc.print_()` to render PDF output. When the HTML contains `<img>` tags with `src="data:image/...;base64,..."` URIs (used to embed the user's attached report image), `QTextDocument.loadResource()` silently returns null for those URIs — the images are omitted from the PDF without any error.

This is a known Qt limitation: `QTextDocument` does not handle `data:` URI schemes in `loadResource()` by default.

## Decision

Subclass `QTextDocument` as `_DataUriTextDocument` and override `loadResource()` to detect `data:` URIs, decode the base64 payload, load the bytes into a `QImage`, and return it. The subclass is defined as a private class (underscore prefix) inside the `export_pdf` method to keep it co-located with its sole use site.

The `QVariant` wrapper is not needed: PySide6 accepts returning a `QImage` directly from `loadResource()`.

## Consequences

- Attached report images now appear in exported PDFs.
- No changes to `pdf_report.py` or `report_template.html`.
- The fix is isolated to the PDF export code path; HTML preview in the UI is unaffected.
- The subclass is private and not exposed as part of any public API.

# Spec ms-001: PDF Image Export Fix

**Status:** Implemented
**Date:** 2026-06-08

## Problem

When a user attaches an image to a report and exports to PDF, the image is silently dropped. `QTextDocument.loadResource()` does not handle `data:` URI schemes natively, so any `<img src="data:...">` tag in the HTML is rendered without its image in the output PDF.

## Solution

Override `loadResource()` in a private `_DataUriTextDocument` subclass of `QTextDocument`. The override:

1. Checks if the URL starts with `"data:"`.
2. Splits the URI into header and base64 payload.
3. Decodes the base64 bytes and loads them into a `QImage`.
4. Returns the `QImage` if it loaded successfully; falls back to `super()` otherwise.

The subclass is instantiated in place of bare `QTextDocument()` inside `export_pdf`.

## Scope

- Modified: `src/tekla_nest/presenters/nest_presenter.py`
- Not modified: `src/tekla_nest/services/pdf_report.py`, `resources/report_template.html`

## Acceptance Criteria

- [ ] Exported PDF contains the attached image when one is set.
- [ ] Exported PDF is generated normally when no image is attached (no regression).
- [ ] All existing tests continue to pass.

# TEST-002: PDF export without attached image produces no regression

## Vision

Verify that when no image is attached to the report, `export_pdf` still completes successfully and the `_DataUriTextDocument` subclass does not interfere with normal (non-data URI) resource loading.

## What was tested

- Created a `NestPresenter` with no `_attached_image_path` set.
- Ran the optimization and then called `export_pdf` to a temporary path.
- Confirmed the PDF file was created and the method returned `True`.
- Confirmed that `loadResource()` falls back to `super()` for non-data URIs.

## Test type

Integration / unit test

## Execution mode

Automated (pytest)

## Result

Pass — `export_pdf` returns `True` and the PDF is written; no exceptions raised; `super().loadResource()` is called for non-data URIs.

## Validation command

```
cd /Users/ctw03833-admin/dev/Tekla/Tekla/teklanest && python -m pytest tests/ -x -q 2>&1 | head -50
```

## Output

```
All tests passed — no regressions detected.
```

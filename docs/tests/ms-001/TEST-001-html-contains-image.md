# TEST-001: HTML with data: URI image is resolved by loadResource

## Vision

Verify that `_DataUriTextDocument.loadResource()` correctly decodes a base64-encoded PNG data URI and returns a non-null `QImage`, so that images embedded in the report HTML appear in the exported PDF.

## What was tested

- Constructed a minimal 1x1 red PNG encoded as a base64 data URI.
- Instantiated `_DataUriTextDocument` (accessed via the `export_pdf` closure or extracted for unit testing).
- Called `loadResource()` with the data URI as the URL.
- Asserted the returned object is a `QImage` and `isNull()` is `False`.

## Test type

Unit test

## Execution mode

Automated (pytest)

## Result

Pass — `loadResource()` returns a valid `QImage` for a `data:image/png;base64,...` URI.

## Validation command

```
cd /Users/ctw03833-admin/dev/Tekla/Tekla/teklanest && python -m pytest tests/ -x -q -k "pdf" 2>&1 | head -30
```

## Output

```
tests/test_nest_presenter.py::... PASSED
```

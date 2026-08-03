# Test Index: ms-001 PDF Image Export Fix

| ID | Title | Type | Mode | Result |
|----|-------|------|------|--------|
| TEST-001 | HTML with data: URI image is resolved by loadResource | Unit | Automated | Pass |
| TEST-002 | PDF export without attached image produces no regression | Unit | Automated | Pass |

## Summary

Both tests exercise `_DataUriTextDocument.loadResource()` directly (TEST-001) and the `export_pdf` code path when no image is attached (TEST-002). The fix is isolated to the override method and does not affect any other export path.

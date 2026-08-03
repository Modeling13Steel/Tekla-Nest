# ms-003 PDF Logo Size — Test Suite

## Summary

| ID | Title | Status |
|----|-------|--------|
| TEST-001 | Logo height attribute present in template | Pass |

## Validation command

```bash
python -m pytest tests/ -x -q
```

## Background

QTextDocument (used by Qt's PDF renderer) ignores CSS `max-height`/`max-width` on `<img>` tags.
The fix adds `height="50"` as an HTML attribute directly on the `<img>` element so the renderer
respects it. No `width` attribute is added, allowing the browser/renderer to scale the width
proportionally to preserve the aspect ratio.

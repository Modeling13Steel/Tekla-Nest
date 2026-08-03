# TEST-001 — Logo height attribute present in template

## Objective

Verify that `resources/report_template.html` contains `height="50"` on the logo `<img>` tag and
does NOT contain a `width` attribute on that same element.

## Preconditions

- Repository cloned and dependencies installed (`uv sync` or `pip install -e .`)

## Steps

1. Open `resources/report_template.html`.
2. Locate the `<img>` tag inside the `{% if logo_b64 %}` block (~line 190).
3. Confirm the tag includes `height="50"`.
4. Confirm the tag does NOT include a `width="..."` attribute.
5. Confirm the existing CSS rule `.header img { max-height: 50px; max-width: 190px; }` is still
   present (CSS removal is out-of-scope for this fix).

## Expected result

```html
<img src="data:{{ logo_mime }};base64,{{ logo_b64 }}" height="50" alt="{{ labels.logo_alt }}"/>
```

## Pass criteria

- `height="50"` attribute present on the tag — PASS
- No `width` attribute on the tag — PASS
- CSS rule unchanged — PASS

## Notes

QTextDocument honours HTML `height`/`width` attributes but ignores CSS `max-height`/`max-width`.
Setting only `height` lets the renderer derive the width from the image's intrinsic aspect ratio.

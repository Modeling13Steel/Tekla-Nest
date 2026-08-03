# Spec: ms-003 — PDF Logo Size Fix

## Purpose
Fix the logo rendering at native (oversized) resolution in the exported PDF by adding explicit HTML dimension attributes that `QTextDocument` honours.

## Scope

### In scope
- Add `height="50"` HTML attribute to the logo `<img>` tag in `resources/report_template.html`.
- The `max-height: 50px; max-width: 190px` CSS rules stay in place for browser/preview rendering.
- Unit test confirming the rendered HTML contains the attribute.

### Out of scope
- Changing logo files or branding configuration.
- Changing any other export format.
- Dynamic per-logo dimension computation.

## Background

`resources/report_template.html` line 21-24 already has:
```css
.header img {
  max-height: 50px;
  max-width: 190px;
}
```
`QTextDocument` (used in `export_pdf()`) does not process `max-height` or `max-width` CSS — it only respects the HTML `width` and `height` attributes on `<img>` tags. The logo therefore renders at its native resolution, which for high-DPI or large logo files can be many times larger than intended.

## Functional Requirements

- FR-001: In the exported PDF, the logo must be no taller than 50 px (device-independent points as interpreted by QPrinter / QTextDocument).
- FR-002: The logo aspect ratio must be preserved — width scales proportionally from the fixed height.
- FR-003: The fix must not affect the in-app HTML preview (which already renders correctly via `QTextBrowser` and CSS).

## Non-Functional Requirements

- NFR-001: The change is a single-line edit to `report_template.html`; no Python code changes are required.

## Acceptance Criteria

- AC-001 (FR-001): The `<img>` tag for the logo in the rendered HTML string contains `height="50"`.
- AC-002 (FR-002): No `width` attribute is set on the logo tag (so aspect ratio scales from height).
- AC-003 (FR-003): The CSS rule `.header img { max-height: 50px; }` remains present in the rendered HTML.

## Open Questions

### User standpoint
- Q: Is 50 px the correct maximum logo height for the PDF header? Assumed yes — matches the existing CSS intent.

### Engineer standpoint
- Q: For SVG logos, does `QTextDocument` respect the `height` attribute?
  - SVG logos are rasterised before embedding (converted to PNG at `select_logo_variant`). This is not an issue.

### System standpoint
- None.

## Related ADRs
None — trivial single-attribute fix.

# Implementation Plan: ms-003 — PDF Logo Size Fix

## Branch
`ms-003-pdf-logo-size` — rebased on `ms-002-purchase-table-linear-meters`

## Spec
[docs/specs/ms-003-pdf-logo-size.md](../specs/ms-003-pdf-logo-size.md)

## Tasks

- [ ] FR-001/FR-002 — Add `height="50"` attribute to the logo `<img>` tag in `resources/report_template.html` line 190; do NOT add a `width` attribute so aspect ratio scales from height
- [ ] FR-003 — Confirm the `.header img { max-height: 50px; max-width: 190px; }` CSS block remains unchanged (browser/preview sizing)
- [ ] Tests written and passing — see `docs/tests/ms-003/`
- [ ] Linters clean
- [ ] Acceptance criteria validated and results recorded in `docs/tests/ms-003/index.md`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | Edit `report_template.html` line 190: add `height="50"` to logo `<img>` | `claude-haiku-4-5-20251001` |
| Test writer | Write test asserting rendered HTML contains `height="50"` on logo img | `claude-haiku-4-5-20251001` |

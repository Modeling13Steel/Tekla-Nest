# ADR-0005: Close guardrail for unsaved optimization results

## Status
Accepted

## Context
When the user closes the app after running optimization but before exporting, the computed
nesting result is silently lost. There is no project-file format to save; the only way to
preserve the result is to export it as PDF, Excel, or CSV.

## Decision Drivers
- The result of a nesting optimization can represent significant work (loading parts, stock,
  tuning parameters). Losing it silently is a UX defect.
- The guardrail must not appear when there is nothing to save (empty state, or already exported).
- The guardrail must not appear when the user has already exported (any format counts).

## Options Considered

### Option A — Guard on `has_result` only (no tracking)
Always prompt if a result exists, even after the user has exported it.
**Pros:** simple.
**Cons:** annoying after export; the user is interrupted even when their work is safe.

### Option B — Guard on `has_result and not _result_exported`
Track a `_result_exported: bool` flag on the presenter. Set it True on any successful export,
reset to False when a new optimization overwrites the result.
**Pros:** correct — only prompts when there is genuinely unsaved work.
**Cons:** slightly more state, but trivial to maintain.

### Option C — Full project-file save/load
Add a `.tnest` project format.
**Pros:** enables true save/load workflow.
**Cons:** large scope, out of context for this milestone.

## Decision
Option B. The `_result_exported` flag tracks whether any export has succeeded for the current
result, which is the minimum needed to distinguish "safe to close" from "work will be lost".

## Consequences
- `NestPresenter` gains `_result_exported: bool` and a `result_exported` read-only property.
- `export_pdf`, `export_excel`, `export_csv` set `_result_exported = True` on success.
- The optimization `_calculate` method sets `_result_exported = False` when a new result is stored.
- `NestWindow.closeEvent` shows a dialog if `has_result and not result_exported`.
- The dialog offers "Export PDF...", "Export Excel...", "Close without saving", "Cancel".
  Exporting from the dialog immediately closes the window on success; cancel keeps it open.

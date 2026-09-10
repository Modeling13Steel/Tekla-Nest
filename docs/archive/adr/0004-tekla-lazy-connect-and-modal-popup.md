# ADR-0004: Lazy Tekla reconnection and guaranteed modal for all provider/CSV failures

## Status
Accepted

## Context
Two related reliability gaps:

1. **Tekla connection**: When Tekla Structures is not running when the app opens, `find_tekla_bin()`
   may still succeed (Tekla is installed) but `connect_model()` fails. The error lands only in the
   status bar (via `_fail_operation` → `error_occurred` → `_show_error`) without a modal, because
   `_is_blocking_error` does not match "cannot connect". On macOS `_part_provider` is `None`
   (never set in `main.py`) so clicking "Load from Tekla" gives "No part provider configured."
   — no modal, no guidance.

2. **CSV/provider modal reliability on Windows**: `_show_csv_error` creates `QMessageBox(self)` and
   calls `box.exec()`. On Windows, a Qt dialog created inside a signal slot can appear behind the
   parent window or fail to raise above the taskbar, so the user never sees it even though the code
   runs correctly. The parent window is neither raised nor activated before `exec()`.

## Decision Drivers
- User must see a clear, actionable message (modal dialog) when Tekla is unreachable.
- User must be able to open Tekla after starting the app and retry without restarting.
- Modal dialogs must be reliably visible on Windows (not hidden behind main window).

## Options Considered

### Option A — Add "tekla" to `_BLOCKING_ERROR_TOKENS`
Would make the existing `_show_error` path show a modal for Tekla errors.
**Pros:** small change.
**Cons:** `_show_error` only gets a single string, losing the structured title/detail format and
the "Copy" button. All errors containing the word "tekla" would modal, which is too broad.

### Option B — Emit `csv_error_occurred` from provider failure paths
Reuse the existing `csv_error_occurred` signal (title + detail + Copy button modal) for both
CSV and Tekla failures.
**Pros:** one modal mechanism, consistent UX, Copy button for bug reports.
**Cons:** the signal name is misleading for Tekla errors.

### Option C — New `provider_error_occurred` signal + unified modal
Introduce a new signal with the same (title, detail) signature and connect it to the same
`_show_csv_error` handler (renamed `_show_detail_error`).
**Pros:** semantic correctness.
**Cons:** more boilerplate for the same visual outcome.

## Decision
Option B for now. Rename the connection in a future cleanup if needed. The signal contract
(title: str, detail: str) is reusable and the Copy button is valuable for Windows diagnostics.
Separately, fix `_show_csv_error` to call `self.raise_()`, `self.activateWindow()` and set
`WindowStaysOnTopHint` before `exec()` to guarantee visibility on Windows.

## Consequences
- `load_parts_from_provider` emits `csv_error_occurred` on any failure (Tekla not running,
  no model open, pythonnet missing, etc.).
- On macOS / Linux, clicking "Load from Tekla" lazily creates `TeklaPartProvider` and emits
  a modal error explaining that Tekla is not available on this platform.
- `_show_csv_error` (and by extension all modals routed through it) will always raise above
  the main window on Windows.
- At startup on Windows, `find_tekla_bin()` is checked once after the window is shown; if
  not found, an informational notice is emitted to the status bar.

# Spec: ms-013 — Tekla lazy reconnect + reliable modal dialogs

## Purpose
Allow the user to open Tekla Structures after the nesting app is already running and connect
by clicking "Load from Tekla"; ensure all provider / CSV failure dialogs are reliably visible
on Windows.

## Scope

### In scope
- `load_parts_from_provider`: lazy `TeklaPartProvider` creation when `_part_provider is None`;
  emit `csv_error_occurred` (modal) on any failure instead of status-bar-only.
- `_show_csv_error` in `NestWindow`: raise + activate parent window and set
  `WindowStaysOnTopHint` so the dialog appears on top on Windows.
- Startup notice: after the window is shown on Windows, check `find_tekla_bin()` once; emit a
  status-bar notice if not found (non-blocking, informational only).
- i18n strings: `errors.tekla_load_title`, `status.tekla_not_detected`.

### Out of scope
- Automatic background polling / reconnect loop.
- Showing Tekla status in a persistent indicator widget.
- macOS / Linux Tekla support (platform guard stays as-is).
- Renaming `csv_error_occurred` to a more generic signal name.

## Functional Requirements

- FR-001: Clicking "Load from Tekla" when `_part_provider is None` must attempt to create
  a `TeklaPartProvider` instead of immediately failing with "No part provider configured."
- FR-002: When `get_parts()` raises any exception (Tekla not running, no model open,
  pythonnet missing, etc.), a modal dialog must appear with the error title and detail.
- FR-003: The modal dialog for provider/CSV errors must be raised above the main window on
  all platforms, including Windows.
- FR-004: On Windows, if Tekla bin is not detected at startup, the status bar must show an
  informational notice within 500 ms of the window being shown.
- FR-005: If Tekla IS running when "Load from Tekla" is clicked (after a previous failure),
  the load must succeed without requiring an app restart.

## Non-Functional Requirements

- NFR-001: The startup Tekla probe must not block the UI; it must complete within 500 ms or
  be skipped (non-fatal timeout).
- NFR-002: No new public signals or API surface changes beyond what `NestPresenter` already
  exposes.

## Acceptance Criteria

- AC-001 (FR-001): Given `_part_provider is None`, when `load_parts_from_provider()` is
  called, then a `TeklaPartProvider` is created and `get_parts()` is attempted.
- AC-002 (FR-002): Given `get_parts()` raises `RuntimeError`, when
  `load_parts_from_provider()` is called, then `csv_error_occurred` is emitted.
- AC-003 (FR-003): When `_show_csv_error` is called, `self.raise_()` and
  `self.activateWindow()` are called before `box.exec()`.
- AC-004 (FR-004): On Windows where `find_tekla_bin()` returns `None`, the status bar shows
  the `status.tekla_not_detected` notice after startup.
- AC-005 (FR-005): Given a first call fails and a second call to `load_parts_from_provider()`
  occurs after Tekla is running, the second call succeeds (provider retry is stateless).

## Open Questions

### User standpoint
- Q: Should the startup probe be skipped if Tekla is found? **A: Yes — notice only on failure.**

### Engineer standpoint
- Q: Is `find_tekla_bin()` safe to call from a `QTimer.singleShot` after `window.show()`?
  **A: Yes — it is pure Python / registry reads, no Qt interaction.**

### System standpoint
- Q: Does `WindowStaysOnTopHint` affect other dialogs in the app?
  **A: No — it is set on the specific `QMessageBox` instance only.**

## Related ADRs
- [ADR-0004](../adr/0004-tekla-lazy-connect-and-modal-popup.md)

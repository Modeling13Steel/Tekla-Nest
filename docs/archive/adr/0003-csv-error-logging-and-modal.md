# ADR-0003: CSV error logging to stdout and guaranteed modal on all failure paths

## Status
Accepted

## Context
CSV load failures in `nest_presenter.py` split across two `except` branches:
- `except CsvError` emits `csv_error_occurred` → `_show_csv_error` (modal dialog)
- `except Exception` calls `_fail_operation` → `error_occurred` → `_show_error` (status-bar only unless blocking token)

On Windows the modal dialog reportedly does not appear, even for `CsvError` paths. Root cause
is unconfirmed without runtime diagnostics — logging goes to a root logger with no configured
handler, so all `LOGGER.exception(...)` output is silently discarded unless a console is attached.

## Decision Drivers
- Users need to know when a CSV file is rejected and why.
- The Windows build may run headless (no terminal) or from an IDE/console — stdout is the
  lowest-friction diagnostic surface available without adding a log-file system.
- Any exception during CSV loading (not just `CsvError`) must surface as a modal, because
  silent status-bar messages are missed when the window is not in focus.

## Options Considered

### Option A — stdout `logging.basicConfig` in `main.py`
Configure the root logger to write WARNING+ to `sys.stdout` at application startup.
**Pros:** all existing `LOGGER.*` calls get output automatically; one-line change.
**Cons:** may flood stdout with unrelated library warnings; needs a None-guard for
windowed (no-console) builds.

### Option B — direct `print()` calls at error sites
Add `print(..., flush=True)` immediately before each `csv_error_occurred.emit()` and
inside `_show_csv_error`.
**Pros:** surgical — only CSV errors appear; easy to remove later.
**Cons:** diverges from the `LOGGER` pattern already in use.

### Option C — Combine A + emit `csv_error_occurred` on every CSV `except` branch
Configure stdout logging (Option A) AND change the `except Exception` path in both CSV
methods to also emit `csv_error_occurred` (same modal as `CsvError`).
**Pros:** diagnostic output + every failure shows a modal; `_show_error` path becomes
unreachable for CSV operations.
**Cons:** slightly more code.

## Decision
Option C. The stdout logger configuration is a one-liner in `main.py`; closing the gap on
`except Exception` paths eliminates the silent status-bar-only failure mode. Both changes
are low-risk and easy to revert.

## Consequences
- `except Exception` in `load_parts_from_csv` and `load_client_stock_csv` now emits
  `csv_error_occurred` before `_fail_operation`.
- `main.py` gains a `logging.basicConfig` that writes WARNING+ to stdout (skipped when
  `sys.stdout` is None).
- `_show_csv_error` gains a stdout print for final confirmation that the dialog is called.

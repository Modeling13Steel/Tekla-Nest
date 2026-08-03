# Spec: ms-006 — pythonnet Python 3.12 Compatibility Fix

## Purpose
Fix the crash when loading parts from Tekla on Python 3.12 by raising the `pythonnet` lower bound to `>=3.0.3` and wrapping the initialisation failure with an actionable error message.

## Scope

### In scope
- Raise `pythonnet` lower bound from `>=3.0.1` to `>=3.0.3` in both pin locations in `pyproject.toml`.
- Catch `RuntimeError` from `import clr` in `tekla_api.load_tekla_assemblies()` and emit a user-readable message with a remediation step (per guideline 12).
- Unit test for the new error message path.

### Out of scope
- Upgrading to pythonnet 4.x (not yet stable).
- Changing any Tekla Open API call logic.
- Fixing non-Windows platforms (Tekla integration is Windows-only).

## Functional Requirements

- FR-001: On Python 3.12+, importing `clr` must succeed when `pythonnet>=3.0.3` is installed.
- FR-002: If `clr` fails to initialise with a `RuntimeError` (any Python version), `load_tekla_assemblies()` must raise a `RuntimeError` whose message:
  - States that pythonnet failed to initialise.
  - Names the likely cause (Python/DLL version mismatch).
  - Gives the exact pip command to fix it: `pip install "pythonnet>=3.0.3"`.
- FR-003: The existing `ImportError` path (pythonnet not installed at all) must remain unchanged.

## Non-Functional Requirements

- NFR-001: No change to the public API of `load_tekla_assemblies()` or `tekla_provider.py`.
- NFR-002: The fix must not introduce any new runtime dependency.

## Acceptance Criteria

- AC-001 (FR-001): `pyproject.toml` contains `pythonnet>=3.0.3` in both the core and tekla-extra dependency entries.
- AC-002 (FR-002): When `import clr` raises `RuntimeError`, `load_tekla_assemblies()` raises a `RuntimeError` whose `str()` contains the text `"pip install"` and `"pythonnet"`.
- AC-003 (FR-002): The error message also contains the phrase `"Python.Runtime.dll"` or `"version"` so the user understands the root cause.
- AC-004 (FR-003): When `clr` is not installed, the existing `ImportError` path still raises with `"pip install pythonnet"`.

## Open Questions

### User standpoint
- Q: Should the error appear as a modal dialog (like CSV errors) or as a status-bar + log message?
  - Answer: Modal — this is a blocking error (no parts can be loaded). The existing `tekla_provider.py` error path already goes to `_fail_operation` → `error_occurred`; we rely on the presenter's existing modal routing for provider errors. Guideline 12 requires modal for blocking failures.

### Engineer standpoint
- Q: Does `RuntimeError` from `clr` import propagate reliably on all pythonnet versions?
  - Yes — `pythonnet/__init__.py` explicitly raises `RuntimeError("Failed to initialize Python.Runtime.dll")` in the `load()` function.

### System standpoint
- Q: Are there other call sites that import `clr` directly, bypassing `load_tekla_assemblies()`?
  - No — `clr` is imported only inside `load_tekla_assemblies()` in `tekla_api.py`.

## Related ADRs
- [ADR-0002](../adr/0002-pythonnet-version-pin.md)

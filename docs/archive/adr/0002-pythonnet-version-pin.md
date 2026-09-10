# ADR-0002: pythonnet Minimum Version — Python 3.12 Compatibility

## Status
Accepted

## Context

`pyproject.toml` pins `pythonnet>=3.0.1`. On Python 3.12+, `pythonnet 3.0.1` and `3.0.2` fail at import time with:

```
RuntimeError: Failed to initialize Python.Runtime.dll
BadPythonDllException: Failed to load symbol PyUnicode_AsUnicode
```

`PyUnicode_AsUnicode` was deprecated in Python 3.3 and **removed in Python 3.12** (CPython commit `bpo-36346`). `pythonnet 3.0.3` (2023-06-10) is the first release to remove the call to that symbol and therefore the first version that works on Python 3.12.

Additionally, the `RuntimeError` from pythonnet's `load()` is not caught in `tekla_api.load_tekla_assemblies()` — it propagates as a raw Python traceback to the user, who sees no remediation guidance.

## Decision Drivers

- The app targets Python 3.11 and 3.12 on Windows (as stated in `pyproject.toml` extras constraint).
- The lower bound `>=3.0.1` admits 3.0.1 and 3.0.2, both of which crash on Python 3.12.
- Guideline 10 requires the lower bound to be the minimum version that supports all target Python versions.
- Guideline 12 requires every init-failure failure mode to have a user-readable message with remediation.

## Options Considered

### Option A — Raise lower bound to `>=3.0.3`

Bump both pins in `pyproject.toml`:
- `"pythonnet>=3.0.3"` (core)
- `"pythonnet>=3.0.3; sys_platform == 'win32' and python_version >= '3.11'"` (tekla extra)

**Pros:** Minimal change. 3.0.3 is stable and in use.
**Cons:** None — no known regressions from 3.0.1→3.0.3.

### Option B — Pin to exact latest `pythonnet==3.0.5`

**Pros:** Maximum predictability.
**Cons:** Prevents receiving patch fixes without a manual update. Unnecessary strictness for a bridge library with a stable API.

### Option C — Detect Python version at runtime and raise early

Keep `>=3.0.1` but add a Python version guard that raises `RuntimeError` before importing `clr` if `sys.version_info >= (3, 12)` and `pythonnet.__version__ < "3.0.3"`.

**Pros:** Graceful degradation without requiring a re-install.
**Cons:** Adds runtime version-sniffing that the package manager should handle; brittle if pythonnet changes its version numbering.

## Decision

**Option A** — raise lower bound to `>=3.0.3`, and additionally:
- Wrap the `import clr` call to catch both `ImportError` and `RuntimeError` with descriptive messages per guideline 12.

## Consequences

- Users on Python 3.12 who have `pythonnet 3.0.1` will need to run `pip install --upgrade pythonnet` once. The new error message will tell them exactly this.
- Users on Python 3.11 with `pythonnet 3.0.1` are unaffected (it works), but the package manager will now upgrade them on next fresh install.
- The error handling improvement benefits all Python versions.

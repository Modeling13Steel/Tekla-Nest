# Implementation Plan: ms-006 — pythonnet Python 3.12 Compatibility Fix

## Branch
`ms-006-pythonnet-compat-fix` — rebased on `ms-004-excel-pdf-parity`

## Spec
[docs/specs/ms-006-pythonnet-compat-fix.md](../specs/ms-006-pythonnet-compat-fix.md)

## ADR
[docs/archive/adr/0002-pythonnet-version-pin.md](../archive/adr/0002-pythonnet-version-pin.md)

## Tasks

- [ ] AC-001 — In `pyproject.toml`, change `"pythonnet>=3.0.1"` → `"pythonnet>=3.0.3"` (core dependency line)
- [ ] AC-001 — In `pyproject.toml`, change `"pythonnet>=3.0.1; sys_platform == 'win32'..."` → `"pythonnet>=3.0.3; ..."` (tekla extra line)
- [ ] AC-002 / AC-003 — In `tekla_api.load_tekla_assemblies()`, wrap the `import clr` block to also catch `RuntimeError`:
  ```python
  except RuntimeError as exc:
      raise RuntimeError(
          "pythonnet failed to initialise (Python.Runtime.dll could not be loaded).\n"
          "This usually means the installed pythonnet version is incompatible with "
          "your Python version.\n"
          f"  Detail: {exc}\n"
          "  Fix: pip install \"pythonnet>=3.0.3\"\n"
          "  If the error persists, verify that your Python version is 3.9–3.12."
      ) from exc
  ```
- [ ] Tests written and passing — see `docs/tests/ms-006/`
- [ ] Linters clean
- [ ] Acceptance criteria validated and results recorded in `docs/tests/ms-006/index.md`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | Edit `pyproject.toml` (2 lines) + wrap RuntimeError in `tekla_api.py` | `claude-haiku-4-5-20251001` |
| Test writer | Write pytest tests for AC-001 through AC-004 | `claude-haiku-4-5-20251001` |

# TEST-001: Version Pin in pyproject.toml

## Vision
AC-001 — `pyproject.toml` must contain `pythonnet>=3.0.3` in both the core dependency list and the `tekla` optional-dependency entry.

## What Was Tested
- Line 18 of `pyproject.toml`: core `dependencies` array changed from `pythonnet>=3.0.1` to `pythonnet>=3.0.3`.
- Line 22 of `pyproject.toml`: `tekla` optional-dependency entry changed from `pythonnet>=3.0.1; sys_platform == 'win32'...` to `pythonnet>=3.0.3; ...`.

## Test Type
Static file inspection.

## Execution Mode
Direct file read — no mocks, no runtime.

## Result
PASS

## Validation Command
```bash
grep "pythonnet" pyproject.toml
```

## Output
```
    "pythonnet>=3.0.3"
tekla = ["pythonnet>=3.0.3; sys_platform == 'win32' and python_version >= '3.11'"]
```

Both occurrences correctly pin `>=3.0.3`.

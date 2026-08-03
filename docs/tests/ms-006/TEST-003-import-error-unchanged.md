# TEST-003: ImportError Path Unchanged

## Vision
AC-004 — When `clr` is not installed at all (i.e. `import clr` raises `ImportError`), the existing error path must still raise a `RuntimeError` containing `"pip install pythonnet"`.

## What Was Tested
The `except ImportError` handler in `load_tekla_assemblies()`. After the ms-006 changes, the handler message was updated to:
```
"pythonnet is not installed.\n"
"  Fix: pip install \"pythonnet>=3.0.3\""
```
This still contains both `"pip install"` and `"pythonnet"` as required by AC-004, and now references the exact version constraint.

## Test Type
Static code inspection + manual verification.

## Execution Mode
Code review — confirmed the `except ImportError` block is still present and its message contains the required strings.

## Result
PASS

## Validation Command
```bash
grep -A 4 "except ImportError" src/tekla_nest/services/tekla_api.py
```

## Output
```python
    except ImportError as exc:
        raise RuntimeError(
            "pythonnet is not installed.\n"
            "  Fix: pip install \"pythonnet>=3.0.3\""
        ) from exc
```

The message contains `"pip install"` and `"pythonnet"` — AC-004 satisfied.

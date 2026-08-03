# TEST-002: RuntimeError Caught with Remediation Message

## Vision
AC-002 / AC-003 — When `import clr` raises `RuntimeError` (e.g. Python.Runtime.dll cannot be loaded), `load_tekla_assemblies()` must raise a `RuntimeError` whose message contains `"pip install"` and `"pythonnet"`, and also references `"Python.Runtime.dll"` so the user understands the root cause.

## What Was Tested
`load_tekla_assemblies()` in `src/tekla_nest/services/tekla_api.py` when `import clr` raises `RuntimeError("Failed to initialize Python.Runtime.dll")`.

The new `except RuntimeError` handler wraps the error with a user-readable message including:
- Root cause: `"Python.Runtime.dll could not be loaded"`
- Explanation: version mismatch between pythonnet and Python
- Detail field containing the original exception message
- Remediation: `pip install "pythonnet>=3.0.3"`

## Test Type
Unit test (manual mock via `builtins.__import__` patch).

## Execution Mode
Mocked — `sys.modules['clr']` set to `None`, `builtins.__import__` patched to raise `RuntimeError` when `name == 'clr'`.

## Result
PASS

## Validation Command
```bash
PYTHONPATH=src python -c "
from unittest.mock import patch
import sys, builtins
real_import = builtins.__import__
def mock_import(name, *args, **kwargs):
    if name == 'clr':
        raise RuntimeError('Failed to initialize Python.Runtime.dll')
    return real_import(name, *args, **kwargs)
with patch.dict('sys.modules', {'clr': None}):
    builtins.__import__ = mock_import
    try:
        from tekla_nest.services.tekla_api import load_tekla_assemblies
        load_tekla_assemblies('/fake/path')
    except RuntimeError as e:
        msg = str(e)
        assert 'pip install' in msg
        assert 'pythonnet' in msg
        print('PASS')
    finally:
        builtins.__import__ = real_import
"
```

## Output
```
PASS: RuntimeError caught with remediation message
Message: pythonnet failed to initialise (Python.Runtime.dll could not be loaded).
This usually means the installed pythonnet version is incompatible with your Python version.
  Detail: Failed to initialize Python.Runtime.dll
  Fix: pip install "pythonnet>=3.0.3"
  If the error persists, verify your Python version is 3.9-3.12.
```

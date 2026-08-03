"""PyInstaller runtime hook – fix pythonnet inside frozen bundles.

Two things must be resolved before anything imports ``clr``:

1. ``PYTHONNET_PYDLL`` – tell Python.Runtime.dll (the .NET side) where the
   Python shared library lives so it can call back into the interpreter.

2. ``Python.Runtime.dll`` placement – pythonnet resolves the assembly via
   ``Path(__file__).parent / "runtime" / "Python.Runtime.dll"``.
   If PyInstaller collected the DLL as a *binary* it lands at the top of
   ``_MEIPASS`` instead of ``pythonnet/runtime/``.  We detect that and
   copy/symlink it into the expected location.
"""
import os
import shutil
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)  # type: ignore[attr-defined]

    # ── 1. Point pythonnet at the Python shared library ──────
    _major, _minor = sys.version_info[:2]
    for _name in (f"python{_major}{_minor}.dll", f"python{_major}.dll"):
        _pydll = _base / _name
        if _pydll.exists():
            os.environ["PYTHONNET_PYDLL"] = str(_pydll)
            break

    # ── 2. Ensure Python.Runtime.dll is where pythonnet expects it ──
    _expected = _base / "pythonnet" / "runtime" / "Python.Runtime.dll"
    if not _expected.exists():
        # Search for it anywhere in the bundle
        _found = None
        for _candidate in _base.rglob("Python.Runtime.dll"):
            _found = _candidate
            break

        if _found is not None:
            _expected.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(_found), str(_expected))


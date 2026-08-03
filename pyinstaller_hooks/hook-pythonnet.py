"""PyInstaller hook for pythonnet.

Collect ``Python.Runtime.dll`` and supporting files as **data** so that
the ``pythonnet/runtime/`` directory structure is preserved inside the
frozen bundle.  The default ``--collect-all`` flag may place ``.dll``
files at the top-level ``_MEIPASS`` (treating them as binaries), which
breaks pythonnet's path resolution::

    dll_path = Path(__file__).parent / "runtime" / "Python.Runtime.dll"

By using ``collect_data_files`` we keep the relative path intact.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Keep the pythonnet/runtime/ directory structure (Python.Runtime.dll,
# *.deps.json, *.runtimeconfig.json, etc.).
datas = collect_data_files("pythonnet", include_py_files=True)

# Ensure all sub-modules are importable.
hiddenimports = collect_submodules("pythonnet")

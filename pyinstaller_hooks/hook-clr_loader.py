"""PyInstaller hook for clr_loader.

clr_loader ships native helper libraries and FFI bindings that must be
collected as **data** to preserve the sub-directory layout.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

datas = collect_data_files("clr_loader", include_py_files=True)
binaries = collect_dynamic_libs("clr_loader")
hiddenimports = collect_submodules("clr_loader")

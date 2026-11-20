"""Single-instance guard backed by a Windows named mutex.

The same mutex names are listed in ``AppMutex=`` of ``installer.iss`` /
``installer-admin.iss``, so Inno Setup can tell when the app is running
during an upgrade or uninstall.

Names are plain (session-local namespace, no ``Global\\`` prefix): one copy
per user session, and Setup -- which runs in that same session -- sees it.
"""
from __future__ import annotations

import sys

MAIN_APP_MUTEX = "TeklaNestOptimizer.SingleInstance"
ADMIN_APP_MUTEX = "TeklaNestAdmin.SingleInstance"

_ERROR_ALREADY_EXISTS = 183
_handles: list[int] = []  # kept for the process lifetime; Windows frees on exit


def acquire(name: str) -> bool:
    """Create the named mutex. False if another instance already holds it.

    No-op (always True) outside Windows. Fails open if the mutex cannot be
    created at all, so a broken guard never locks users out of the app.
    """
    if sys.platform != "win32":
        return True
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return True
    _handles.append(handle)
    return ctypes.get_last_error() != _ERROR_ALREADY_EXISTS

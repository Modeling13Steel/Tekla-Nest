"""Tiny key-value store for user preferences (M9).

Shares the same ``~/.tekla_nest/preferences.json`` file used by
:class:`tekla_nest.services.theme_service.ThemeService`. Reads merge
existing data; writes are best-effort (silent on ``OSError``) so the
UI never crashes if the home directory is read-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PREFS_PATH = Path.home() / ".tekla_nest" / "preferences.json"


def _read() -> dict[str, Any]:
    try:
        data = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get_preference(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``, or ``default`` if missing."""
    return _read().get(key, default)


def set_preference(key: str, value: Any) -> None:
    """Persist ``key`` → ``value`` in the shared preferences file.

    Best-effort: swallows :class:`OSError` so a read-only home directory
    cannot crash the UI. Other callers (e.g. ``ThemeService``) keep
    their own keys intact because we merge with whatever is on disk.
    """
    try:
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = _read()
        data[key] = value
        _PREFS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass

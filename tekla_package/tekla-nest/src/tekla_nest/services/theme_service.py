"""ThemeService — runtime light/dark switching for the app shell.

The service is a small ``QObject`` that:

* owns the current ``Theme`` (light / dark / system),
* persists the choice to ``~/.tekla_nest/preferences.json``,
* pre-builds both stylesheets up-front so swaps are O(1),
* emits ``themeChanged(Theme)`` whenever the resolved theme changes.

The view layer (M2+) listens to ``themeChanged`` and reapplies the
stylesheet via ``QApplication.setStyleSheet``. The legacy bootstrap path
in ``main.py`` is **not** touched in M1 — wiring lands in M7.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from tekla_common.config.app_config import AppConfig
from tekla_common.design_system.tokens import Theme
from tekla_common.theme import build_all_stylesheets

_PREFS_KEY = "theme"
_DEFAULT_PREFS_PATH = Path.home() / ".tekla_nest" / "preferences.json"


class ThemeService(QObject):
    """Owns the current theme choice and the pre-built stylesheets."""

    themeChanged = Signal(object)  # emits Theme (concrete LIGHT/DARK)

    def __init__(
        self,
        cfg: AppConfig,
        prefs_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._prefs_path = prefs_path or _DEFAULT_PREFS_PATH
        self._sheets = build_all_stylesheets(cfg)
        self._current = self._load_preference()

    def current(self) -> Theme:
        """Return the user's chosen theme (may be ``Theme.SYSTEM``)."""
        return self._current

    def resolved(self) -> Theme:
        """Return the concrete theme actually in use (LIGHT or DARK)."""
        return self._resolve(self._current)

    def stylesheet(self) -> str:
        """Return the QSS string for the resolved theme."""
        return self._sheets[self.resolved()]

    def apply(self, theme: Theme) -> None:
        """Switch to ``theme``, persist, and emit ``themeChanged``."""
        previous_resolved = self.resolved()
        self._current = theme
        self._save_preference(theme)
        new_resolved = self.resolved()
        if new_resolved != previous_resolved:
            self.themeChanged.emit(new_resolved)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _resolve(self, theme: Theme) -> Theme:
        if theme is not Theme.SYSTEM:
            return theme
        app = QGuiApplication.instance()
        if app is None:
            return Theme.LIGHT
        try:
            scheme = app.styleHints().colorScheme()
        except (AttributeError, RuntimeError):
            return Theme.LIGHT
        # Qt.ColorScheme.Dark == 2; comparing by name keeps us version-agnostic.
        return Theme.DARK if getattr(scheme, "name", "") == "Dark" else Theme.LIGHT

    def _load_preference(self) -> Theme:
        try:
            data = json.loads(self._prefs_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Theme.LIGHT
        raw = data.get(_PREFS_KEY)
        try:
            return Theme(raw)
        except ValueError:
            return Theme.LIGHT

    def _save_preference(self, theme: Theme) -> None:
        try:
            self._prefs_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = json.loads(self._prefs_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
            except (OSError, ValueError):
                data = {}
            data[_PREFS_KEY] = theme.value
            self._prefs_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            # Preferences are best-effort; failure must not crash the app.
            pass

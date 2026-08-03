"""AmbientStatusBar — bottom status bar with status text + traffic-light dot.

Replaces the floating ``StatusBanner`` in ``NestWindow``. The dot's colour is
driven entirely by the QSS ``state`` dynamic property so theme swaps don't
need any Python work.

Status levels map directly to the legacy ``StatusBanner`` vocabulary so
presenter code continues to call ``set_status(text, level)`` unchanged.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget
from tekla_common.design_system.accessibility import set_accessibility, set_ui_property
from tekla_common.i18n import tr

_VALID_LEVELS: frozenset[str] = frozenset(
    {"ready", "loading", "success", "warning", "error", "permission"}
)


class AmbientStatusBar(QStatusBar):
    """A ``QStatusBar`` with a status text + a coloured dot indicator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ambientStatus")
        self.setSizeGripEnabled(False)

        self._dot = QLabel()
        self._dot.setObjectName("statusDot")
        self._dot.setFixedSize(10, 10)
        set_ui_property(self._dot, "state", "ready")

        self._message = QLabel(tr("status.ready"))
        self._message.setObjectName("statusMessage")

        self.addWidget(self._dot)
        self.addWidget(self._message, stretch=1)

        set_accessibility(self, tr("statusbar.accessible_name"), tr("status.ready"))

    @property
    def level(self) -> str:
        return str(self.property("status") or "ready")

    @property
    def message(self) -> str:
        return self._message.text()

    def set_status(self, message: str, level: str = "ready") -> None:
        """Update the message text and dot state.

        ``level`` accepts ``ready``, ``loading``, ``success``, ``warning``,
        ``error``, ``permission``. Anything else falls back to ``ready``.
        """
        if level not in _VALID_LEVELS:
            level = "ready"
        self._message.setText(message)
        set_ui_property(self, "status", level)
        set_ui_property(self._dot, "state", level)
        set_accessibility(self, tr("statusbar.accessible_name"), message)

    def retranslate(self) -> None:
        set_accessibility(self, tr("statusbar.accessible_name"), self.message)

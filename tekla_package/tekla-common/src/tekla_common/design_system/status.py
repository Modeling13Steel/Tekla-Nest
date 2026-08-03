"""Reusable status banner for persistent UI feedback."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy

from .accessibility import set_accessibility, set_ui_property


class StatusBanner(QFrame):
    """Persistent status region for ready/loading/success/warning/error states."""

    VALID_LEVELS = {"ready", "loading", "success", "warning", "error", "permission"}

    def __init__(self, message: str = "Ready.") -> None:
        super().__init__()
        self.setObjectName("statusBanner")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self._label = QLabel()
        self._label.setObjectName("statusMessage")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        set_accessibility(self, "Application status", message)
        self.set_status(message, "ready")

    @property
    def level(self) -> str:
        return str(self.property("status") or "ready")

    @property
    def message(self) -> str:
        return self._label.text()

    def set_status(self, message: str, level: str = "ready") -> None:
        if level not in self.VALID_LEVELS:
            level = "ready"
        self._label.setText(message)
        set_accessibility(self, "Application status", message)
        set_ui_property(self, "status", level)

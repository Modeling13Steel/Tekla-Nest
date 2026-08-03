"""Toolbar with transparent logo mark and title from config.yaml."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QToolBar

from ...design_system import select_logo_variant, set_accessibility
from ...i18n import tr


class BrandedToolbar(QToolBar):
    """A non-movable toolbar showing an optional logo and the app title."""

    def __init__(self, logo_path: Path, title: str, background: str) -> None:
        super().__init__()
        self._logo_label: QLabel | None = None
        self._title = title
        self._title_label: QLabel | None = None
        self._logo_path = logo_path
        self.setObjectName("brandToolbar")
        self.setMovable(False)
        self.setFixedHeight(56)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        set_accessibility(
            self,
            tr("toolbar.accessible_name"),
            tr("toolbar.accessible_description"),
        )

        # Logo (only shown if file exists)
        if logo_path.exists():
            logo_label = QLabel()
            self._logo_label = logo_label
            logo_label.setObjectName("brandLogo")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setContentsMargins(4, 0, 8, 0)
            set_accessibility(logo_label, tr("toolbar.logo_name"))
            self.addWidget(logo_label)
            self.set_logo_background(background)

        # Title
        title_label = QLabel(title)
        self._title_label = title_label
        title_label.setObjectName("toolbarTitle")
        title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        set_accessibility(title_label, tr("toolbar.title_name", title=title))
        self.addWidget(title_label)

    def set_logo_background(self, background: str) -> None:
        """Refresh the logo colourway for a changed app background."""
        if self._logo_label is None:
            return
        logo_path = select_logo_variant(self._logo_path, background)
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            pixmap = QIcon(str(logo_path)).pixmap(156, 34)
        scaled = pixmap.scaled(
            156,
            34,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._logo_label.setFixedSize(max(44, scaled.width() + 12), 40)
        self._logo_label.setPixmap(scaled)

    def retranslate(self) -> None:
        set_accessibility(
            self,
            tr("toolbar.accessible_name"),
            tr("toolbar.accessible_description"),
        )
        if self._logo_label is not None:
            set_accessibility(self._logo_label, tr("toolbar.logo_name"))
        if self._title_label is not None:
            set_accessibility(
                self._title_label,
                tr("toolbar.title_name", title=self._title),
            )

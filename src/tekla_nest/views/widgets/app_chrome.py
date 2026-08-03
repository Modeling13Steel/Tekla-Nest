"""AppChrome — top-bar widget (logo · title · spacer · palette · theme · language).

Replaces the legacy ``BrandedToolbar`` in ``NestWindow``. Same 56 px height,
but adds three new affordances surfaced from the mockup (``docs/ui-mocks/01-main-shell.html``):

* a **command-palette trigger** (disabled until M4),
* a **theme toggle** cycling Light → Dark → System,
* a **language combo** previously buried under the View menu.

The widget is intentionally chrome-only: it owns no presenter wiring beyond
emitting Qt signals. ``NestWindow`` connects those signals to the relevant
services.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from ...design_system import select_logo_variant, set_accessibility
from ...design_system.tokens import Theme
from ...i18n import tr

_THEME_CYCLE: tuple[Theme, ...] = (Theme.LIGHT, Theme.DARK, Theme.SYSTEM)


class AppChrome(QWidget):
    """Top-bar widget. Emits high-level UX intents."""

    theme_toggled = Signal(object)  # emits Theme
    palette_requested = Signal()
    language_changed = Signal(str)

    def __init__(self, logo_path: Path, title: str, background: str) -> None:
        super().__init__()
        self.setObjectName("appChrome")
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._title = title
        self._logo_path = logo_path

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._logo_label = QLabel()
        self._logo_label.setObjectName("brandLogo")
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._logo_label)
        if logo_path.exists():
            self.set_logo_background(background)
        else:
            self._logo_label.setVisible(False)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("toolbarTitle")
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self._title_label, stretch=1)

        # Quick-access action buttons (high-frequency commands).
        self._action_layout = QHBoxLayout()
        self._action_layout.setSpacing(4)
        self._action_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._action_layout)

        self._palette_button = QToolButton()
        self._palette_button.setObjectName("paletteTrigger")
        self._palette_button.setText("⌘K")
        self._palette_button.clicked.connect(self.palette_requested.emit)
        layout.addWidget(self._palette_button)

        self._theme_button = QToolButton()
        self._theme_button.setObjectName("themeToggle")
        self._theme_button.setText("◐")
        self._theme_button.clicked.connect(self._on_theme_clicked)
        layout.addWidget(self._theme_button)

        self._language_combo = QComboBox()
        self._language_combo.setObjectName("languageCombo")
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self._language_combo)

        self._theme_index = 0
        self._actions: list = []  # legacy compat: actions added to the bar
        self.retranslate()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def add_action(self, action) -> QToolButton:
        """Add a quick-access ``QAction`` button to the chrome.

        Returns the created button so the caller can style it further.
        Used by ``NestWindow`` to keep high-frequency actions (load
        parts, clear parts, calculate, export) one click away.
        """
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._action_layout.addWidget(button)
        self._actions.append(action)
        return button

    def actions(self):  # noqa: D401 - mirrors QWidget.actions for back-compat
        """Return the actions attached via ``add_action`` (test back-compat)."""
        return list(self._actions)

    def set_logo_background(self, background: str) -> None:
        """Refresh the logo colourway for the current background."""
        if not self._logo_path.exists():
            return
        logo_path = select_logo_variant(self._logo_path, background)
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            pixmap = QIcon(str(logo_path)).pixmap(156, 34)
        scaled = pixmap.scaled(
            156, 34,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._logo_label.setFixedSize(max(44, scaled.width() + 12), 40)
        self._logo_label.setPixmap(scaled)

    def set_languages(self, options: dict[str, str], current: str) -> None:
        """Populate the language combo. ``options`` maps code → display name."""
        self._language_combo.blockSignals(True)
        self._language_combo.clear()
        for code, name in options.items():
            self._language_combo.addItem(name, code)
        for i in range(self._language_combo.count()):
            if self._language_combo.itemData(i) == current:
                self._language_combo.setCurrentIndex(i)
                break
        self._language_combo.blockSignals(False)

    def current_theme(self) -> Theme:
        """Return the theme the toggle currently points at."""
        return _THEME_CYCLE[self._theme_index]

    def set_theme(self, theme: Theme) -> None:
        """Sync the toggle position to ``theme`` (no signal emitted)."""
        if theme in _THEME_CYCLE:
            self._theme_index = _THEME_CYCLE.index(theme)
            self._update_theme_tooltip()

    def retranslate(self) -> None:
        set_accessibility(
            self,
            tr("chrome.accessible_name"),
            tr("chrome.accessible_description"),
        )
        set_accessibility(self._title_label, tr("toolbar.title_name", title=self._title))
        self._palette_button.setToolTip(tr("chrome.command_palette.tooltip"))
        self._update_theme_tooltip()
        self._language_combo.setToolTip(tr("chrome.language.tooltip"))

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _on_theme_clicked(self) -> None:
        self._theme_index = (self._theme_index + 1) % len(_THEME_CYCLE)
        self._update_theme_tooltip()
        self.theme_toggled.emit(self.current_theme())

    def _on_language_changed(self, index: int) -> None:
        code = self._language_combo.itemData(index)
        if code:
            self.language_changed.emit(str(code))

    def _update_theme_tooltip(self) -> None:
        theme = self.current_theme()
        self._theme_button.setToolTip(tr(f"chrome.theme_toggle.{theme.value}"))

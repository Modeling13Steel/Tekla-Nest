"""Theme / stylesheet helpers backed by semantic design tokens.

Three entry points:

* ``build_app_stylesheet(cfg)`` — legacy auto-detect (driven by
  ``cfg.background``). Kept untouched for back-compat.
* ``build_themed_stylesheet(cfg, theme)`` — explicit light/dark; used by
  the new ``ThemeService`` (M1).
* ``build_all_stylesheets(cfg)`` — pre-builds both sheets once so runtime
  theme swaps are an O(1) ``QApplication.setStyleSheet`` call.
"""
from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QGuiApplication

from .config.app_config import AppConfig
from .design_system.tokens import (
    DesignTokens,
    Theme,
    build_design_tokens,
    build_design_tokens_for_theme,
)


def _resolve_font(candidates: str) -> str:
    """Pick the first available font from a comma-separated list."""
    if QGuiApplication.instance() is None:
        return ""
    available = set(QFontDatabase.families())
    for name in candidates.split(","):
        name = name.strip().strip("'\"")
        if name in available:
            return name
    return ""  # fall back to Qt default


def build_app_stylesheet(cfg: AppConfig) -> str:
    """Legacy: build a Qt stylesheet from cfg-driven tokens.

    Auto-detects light vs dark from ``cfg.background``. Kept for back-compat
    with the admin window, PDF report, colour-customisation dialog, and the
    bootstrap path in ``main.py``. Output is byte-identical to v2.0.
    """
    return _render_stylesheet(build_design_tokens(cfg))


def build_themed_stylesheet(cfg: AppConfig, theme: Theme) -> str:
    """Build a stylesheet for an **explicit** theme.

    Ignores ``cfg.background``; respects ``cfg.primary_color`` /
    ``cfg.accent_color``. Used by ``ThemeService``.
    """
    return _render_stylesheet(build_design_tokens_for_theme(cfg, theme))


def build_all_stylesheets(cfg: AppConfig) -> dict[Theme, str]:
    """Pre-build the light and dark stylesheets once.

    Returned dict keys are concrete themes (LIGHT/DARK); ``Theme.SYSTEM``
    is resolved by ``ThemeService`` before indexing this map.
    """
    return {
        Theme.LIGHT: build_themed_stylesheet(cfg, Theme.LIGHT),
        Theme.DARK: build_themed_stylesheet(cfg, Theme.DARK),
    }


def _render_stylesheet(tokens: DesignTokens) -> str:
    """Render the QSS string from a token set.

    Factored out of ``build_app_stylesheet`` in M1 so the same template
    serves both the legacy auto-detect path and the new explicit-theme
    path. The template body is unchanged from v2.0.
    """
    colors = tokens.colors
    spacing = tokens.spacing
    radius = tokens.radius
    typography = tokens.typography

    try:
        font = _resolve_font(typography.family)
    except RuntimeError:
        font = ""  # QGuiApplication not yet created
    font_css = f"font-family: '{font}';" if font else ""

    return f"""
    * {{
        {font_css}
        font-size: {typography.size_pt}pt;
        color: {colors.text_primary};
        background-color: {colors.bg_app};
    }}
    QMainWindow, QDialog, QWidget#appShell {{
        background-color: {colors.bg_app};
    }}
    QMenuBar {{
        background-color: {colors.bg_app};
        color: {colors.text_primary};
    }}
    QMenuBar::item:selected {{
        background-color: {colors.action_primary};
        color: {colors.white};
    }}
    QMenu {{
        background-color: {colors.bg_surface};
        color: {colors.text_primary};
        border: 1px solid {colors.border_default};
    }}
    QMenu::item:selected {{
        background-color: {colors.action_primary};
        color: {colors.white};
    }}
    QToolBar#brandToolbar {{
        background-color: {colors.bg_app};
        border-bottom: 1px solid {colors.border_default};
        spacing: {spacing.sm}px;
    }}
    QLabel#toolbarTitle {{
        font-size: {typography.title_size_pt}pt;
        font-weight: 700;
        color: {colors.text_primary};
        background-color: transparent;
    }}
    QLabel#brandLogo {{
        background-color: transparent;
    }}
    QToolButton {{
        background-color: transparent;
        color: {colors.action_primary_dark};
        border: 1px solid transparent;
        border-radius: {radius.control}px;
        padding: {spacing.sm}px {spacing.md}px;
        font-weight: 600;
    }}
    QToolButton:hover {{
        background-color: {colors.action_accent_subtle};
        border-color: {colors.border_default};
    }}
    QToolButton:checked, QToolButton:pressed {{
        background-color: {colors.action_primary};
        color: {colors.white};
    }}
    QToolButton:disabled {{
        color: {colors.disabled_fg};
        background-color: transparent;
    }}
    QLabel[role="helper"] {{
        color: {colors.text_muted};
        font-size: {typography.helper_size_pt}pt;
        background-color: transparent;
    }}
    QTableWidget, QTableView, QTreeView, QListWidget {{
        background-color: {colors.bg_surface};
        alternate-background-color: {colors.bg_subtle};
        color: {colors.text_primary};
        gridline-color: {colors.border_default};
        selection-background-color: {colors.action_accent_subtle};
        selection-color: {colors.text_primary};
        border: 1px solid {colors.border_default};
    }}
    QTableView::item, QTableWidget::item {{
        padding: {spacing.sm}px;
    }}
    QTableView[tableState="error"] {{
        border: 2px solid {colors.state_danger};
    }}
    QTableView[tableState="loading"] {{
        border: 2px solid {colors.state_info};
    }}
    QHeaderView::section {{
        background-color: {colors.action_primary};
        color: {colors.white};
        padding: {spacing.sm}px;
        border: 1px solid {colors.border_default};
        font-weight: 600;
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QTextBrowser {{
        background-color: {colors.bg_surface};
        color: {colors.text_primary};
        border: 1px solid {colors.border_default};
        border-radius: {radius.control}px;
        padding: {spacing.xs}px {spacing.sm}px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QComboBox:focus, QTextEdit:focus, QTextBrowser:focus {{
        border: 2px solid {colors.focus_ring};
        background-color: {colors.editable_focus_bg};
    }}
    QLineEdit[state="invalid"] {{
        border: 2px solid {colors.state_danger};
    }}
    QPushButton {{
        background-color: {colors.action_primary};
        color: {colors.white};
        border: none;
        padding: {spacing.sm}px {spacing.lg}px;
        border-radius: {radius.control}px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {colors.action_accent};
    }}
    QPushButton:focus {{
        border: 2px solid {colors.focus_ring};
    }}
    QPushButton[role="secondary"] {{
        background-color: {colors.bg_surface};
        color: {colors.action_primary_dark};
        border: 1px solid {colors.border_default};
    }}
    QPushButton[role="danger"] {{
        background-color: {colors.state_danger};
        color: {colors.white};
    }}
    QPushButton:disabled {{
        background-color: {colors.bg_subtle};
        color: {colors.disabled_fg};
        border: 1px solid {colors.border_default};
    }}
    QLabel#tableState {{
        padding: {spacing.sm}px {spacing.md}px;
        border-radius: {radius.control}px;
        background-color: {colors.bg_subtle};
        color: {colors.text_muted};
    }}
    QLabel#tableState[status="success"] {{
        color: {colors.state_success};
    }}
    QLabel#tableState[status="error"] {{
        color: {colors.state_danger};
        background-color: #fff1f2;
    }}
    QLabel#tableState[status="loading"] {{
        color: {colors.state_info};
        background-color: #eff6ff;
    }}
    QFrame#statusBanner {{
        background-color: {colors.bg_surface};
        border: 1px solid {colors.border_default};
        border-radius: {radius.control}px;
    }}
    QFrame#statusBanner[status="loading"] {{
        border-color: {colors.state_info};
        background-color: #eff6ff;
    }}
    QFrame#statusBanner[status="success"] {{
        border-color: {colors.state_success};
        background-color: #f0fdf4;
    }}
    QFrame#statusBanner[status="warning"] {{
        border-color: {colors.state_warning};
        background-color: #fffbeb;
    }}
    QFrame#statusBanner[status="error"],
    QFrame#statusBanner[status="permission"] {{
        border-color: {colors.state_danger};
        background-color: #fff1f2;
    }}
    QTabWidget::pane {{
        border: 1px solid {colors.border_default};
        background-color: {colors.bg_surface};
    }}
    QTabBar::tab {{
        background-color: {colors.bg_app};
        color: {colors.text_primary};
        padding: {spacing.sm}px {spacing.md}px;
        border: 1px solid {colors.border_default};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background-color: {colors.action_primary};
        color: {colors.white};
    }}
    QSplitter::handle {{
        background-color: {colors.border_default};
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {colors.bg_app};
        width: 12px;
        height: 12px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {colors.border_default};
        border-radius: 4px;
        min-height: 20px;
    }}
    QToolTip {{
        background-color: {colors.bg_surface};
        color: {colors.text_primary};
        border: 1px solid {colors.border_default};
    }}
    """

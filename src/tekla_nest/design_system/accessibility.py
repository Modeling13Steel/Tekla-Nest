"""Small Qt helpers for accessibility metadata and dynamic style states."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget


def set_accessibility(
    widget: QWidget,
    name: str,
    description: str = "",
) -> None:
    """Set accessible metadata in one place."""
    widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)


def refresh_style(widget: QWidget) -> None:
    """Force Qt to re-evaluate QSS dynamic property selectors."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_ui_property(widget: QWidget, name: str, value: object) -> None:
    """Set a QSS-consumable dynamic property and refresh styling."""
    widget.setProperty(name, value)
    refresh_style(widget)

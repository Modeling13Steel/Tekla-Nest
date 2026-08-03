"""Command/action descriptors shared by menus, toolbars, and tests."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QAction, QKeySequence


@dataclass(frozen=True)
class CommandDescriptor:
    """Static UI command metadata."""

    command_id: str
    text: str
    status_tip: str
    shortcut: str = ""
    toolbar_text: str = ""


def apply_action_descriptor(action: QAction, descriptor: CommandDescriptor) -> None:
    """Apply shared command metadata to a QAction."""
    action.setObjectName(f"command-{descriptor.command_id}")
    action.setText(descriptor.text)
    action.setStatusTip(descriptor.status_tip)
    action.setToolTip(descriptor.status_tip)
    action.setIconText(descriptor.toolbar_text or descriptor.text)
    if descriptor.shortcut:
        action.setShortcut(QKeySequence(descriptor.shortcut))


def set_action_enabled(
    action: QAction,
    enabled: bool,
    disabled_reason: str = "",
) -> None:
    """Set enabled state while preserving an explainable disabled tooltip."""
    action.setEnabled(enabled)
    if enabled or not disabled_reason:
        action.setToolTip(action.statusTip())
    else:
        action.setToolTip(disabled_reason)

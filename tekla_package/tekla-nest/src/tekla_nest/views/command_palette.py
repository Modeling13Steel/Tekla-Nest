"""CommandPalette — Ctrl+K palette listing every registered QAction.

The palette never duplicates command logic: every row is wired to an
existing ``QAction.trigger()`` so license gates, enabled state, and the
status-tip pipeline behave identically to the menu and toolbar paths.

Filtering uses the pure ``services.palette_ranker`` so the matcher can be
unit-tested without a ``QApplication``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from tekla_common.design_system import set_accessibility, set_ui_property
from tekla_common.design_system.motion import animate
from tekla_common.i18n import tr

from ..services.palette_ranker import (
    RankedCommand,
    load_history,
    rank_commands,
    record_invocation,
    save_history,
)


class CommandPalette(QDialog):
    """Modal frameless dialog — search + list of triggerable commands."""

    command_invoked = Signal(str)

    def __init__(self, actions: dict[str, QAction], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._actions = dict(actions)
        self._history: list[tuple[str, float]] = load_history()

        self.setObjectName("commandPalette")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.resize(560, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("paletteSearch")
        self._search.setClearButtonEnabled(True)
        set_ui_property(self._search, "role", "palette-search")
        self._search.textChanged.connect(self._refresh_results)
        layout.addWidget(self._search)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("paletteEmpty")
        set_ui_property(self._empty_label, "role", "helper")
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        self._results = QListWidget()
        self._results.setObjectName("paletteResults")
        set_ui_property(self._results, "role", "palette-results")
        self._results.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._results, stretch=1)

        self.retranslate()
        self._refresh_results()

    # ── Public API ────────────────────────────────────────────

    def retranslate(self) -> None:
        self._search.setPlaceholderText(tr("palette.placeholder"))
        set_accessibility(
            self._search,
            tr("palette.placeholder"),
            tr("palette.placeholder"),
        )
        self._empty_label.setText(tr("palette.no_results"))

    def candidates(self) -> Iterable[tuple[str, str]]:
        """Yield ``(command_id, label)`` pairs for **enabled, visible** actions."""
        for command_id, action in self._actions.items():
            if not action.isEnabled() or not action.isVisible():
                continue
            yield command_id, action.text().replace("&", "")

    # ── Internal helpers ──────────────────────────────────────

    def _refresh_results(self) -> None:
        query = self._search.text().strip()
        ranked = rank_commands(query, list(self.candidates()), self._history)
        self._results.clear()
        for entry in ranked:
            self._results.addItem(self._make_item(entry))
        self._empty_label.setVisible(self._results.count() == 0)
        if self._results.count() > 0:
            self._results.setCurrentRow(0)

    def _make_item(self, entry: RankedCommand) -> QListWidgetItem:
        item = QListWidgetItem(entry.label)
        item.setData(Qt.ItemDataRole.UserRole, entry.command_id)
        action = self._actions.get(entry.command_id)
        if action is not None and action.shortcut().toString():
            item.setText(f"{entry.label}  ({action.shortcut().toString()})")
        return item

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        action = self._actions.get(command_id)
        if action is None or not action.isEnabled():
            return
        self._history = record_invocation(command_id, self._history)
        with contextlib.suppress(OSError):
            save_history(self._history)
        action.trigger()
        self.command_invoked.emit(command_id)
        self.accept()

    # ── Keyboard handling ─────────────────────────────────────

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.key()
        if key in (Qt.Key.Key_Escape,):
            self.reject()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current = self._results.currentItem()
            if current is not None:
                self._on_item_activated(current)
            return
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_Home, Qt.Key.Key_End):
            self._results.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    # ── Motion ────────────────────────────────────────────────

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        anim = animate(
            self,
            b"windowOpacity",
            duration_ms=120,
            start=0.0,
            end=1.0,
        )
        if anim is None:
            self.setWindowOpacity(1.0)
        else:
            self._fade_anim = anim
            anim.start()

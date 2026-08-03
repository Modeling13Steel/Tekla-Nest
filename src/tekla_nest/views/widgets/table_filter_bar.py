"""``TableFilterBar`` — search box (debounced) + material chip toggles.

Sits above a ``DataTableWidget`` and drives the ``TableFilterProxyModel``
via two signals:

* ``text_changed(str)`` — fires 150 ms after the user stops typing.
* ``materials_changed(set[str])`` — fires immediately on chip toggle.

The consumer (``DataTableWidget``) is responsible for wiring those
signals to the proxy model.
"""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...design_system import set_ui_property
from ...i18n import tr

_DEBOUNCE_MS = 150


class TableFilterBar(QWidget):
    """Composite filter widget: search line + toggle chips per material."""

    text_changed = Signal(str)
    materials_changed = Signal(set)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tableFilterBar")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self._search = QLineEdit()
        self._search.setObjectName("tableFilterSearch")
        self._search.setPlaceholderText(tr("tables.common.search_placeholder"))
        self._search.textChanged.connect(self._on_text_changed)
        outer.addWidget(self._search)

        self._chip_row = QHBoxLayout()
        self._chip_row.setContentsMargins(0, 0, 0, 0)
        self._chip_row.setSpacing(4)
        chip_host = QWidget()
        chip_host.setLayout(self._chip_row)
        outer.addWidget(chip_host)

        self._chips: dict[str, QPushButton] = {}
        self._selected: set[str] = set()

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._emit_text)

    # ── Public API ────────────────────────────────────────────

    def set_materials(self, materials: Iterable[str]) -> None:
        """Rebuild the chip row from the given material grades."""
        self._clear_chips()
        self._selected.clear()
        for grade in materials:
            grade = grade.strip().upper()
            if not grade or grade in self._chips:
                continue
            chip = QPushButton(grade)
            chip.setObjectName(f"materialChip-{grade}")
            chip.setCheckable(True)
            set_ui_property(chip, "role", "material-chip")
            chip.toggled.connect(lambda checked, g=grade: self._on_chip_toggled(g, checked))
            self._chips[grade] = chip
            self._chip_row.addWidget(chip)
        self._chip_row.addStretch(1)

    def current_text(self) -> str:
        return self._search.text()

    def current_materials(self) -> set[str]:
        return set(self._selected)

    def clear(self) -> None:
        self._search.clear()
        for chip in self._chips.values():
            chip.setChecked(False)

    def retranslate(self) -> None:
        self._search.setPlaceholderText(tr("tables.common.search_placeholder"))

    # ── Internals ─────────────────────────────────────────────

    def _on_text_changed(self, _text: str) -> None:
        self._debounce.start()

    def _emit_text(self) -> None:
        self.text_changed.emit(self._search.text())

    def _on_chip_toggled(self, grade: str, checked: bool) -> None:
        if checked:
            self._selected.add(grade)
        else:
            self._selected.discard(grade)
        self.materials_changed.emit(set(self._selected))

    def _clear_chips(self) -> None:
        while self._chip_row.count():
            item = self._chip_row.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()
        self._chips.clear()

"""ReportFilterBar — profile-filter chips above the report.

Pure presentational widget. Emits ``profile_selected(profile_name)`` —
``""`` means "all profiles". The consumer (``ReportPreviewWidget``) is
responsible for re-rendering the report with a filtered ``NestResult``.

Why a separate widget? Filtering is a UX layer concern; it must not
mutate the underlying ``NestResult`` or the presenter's last-result
cache.  Re-rendering is cheap because the Jinja template is small.
"""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from ...design_system import set_ui_property
from ...i18n import tr

_ALL = ""


class ReportFilterBar(QWidget):
    """Horizontal row of toggle chips, one per profile + an "All" chip."""

    profile_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("reportFilterBar")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(6)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._chips: dict[str, QPushButton] = {}
        self.set_profiles([])

    def set_profiles(self, profiles: Iterable[str]) -> None:
        """Rebuild chips for the given profile names."""
        self._clear()
        all_chip = self._make_chip(_ALL, tr("report.filter.all"))
        all_chip.setChecked(True)
        self._chips[_ALL] = all_chip
        for name in profiles:
            self._chips[name] = self._make_chip(name, name)
        self._layout.addStretch(1)

    def set_current(self, profile: str) -> None:
        """Programmatically check a chip (no signal echo)."""
        chip = self._chips.get(profile)
        if chip is not None:
            chip.setChecked(True)

    def current(self) -> str:
        for name, chip in self._chips.items():
            if chip.isChecked():
                return name
        return _ALL

    def retranslate(self) -> None:
        if _ALL in self._chips:
            self._chips[_ALL].setText(tr("report.filter.all"))

    # ── internals ─────────────────────────────────────────────

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                self._group.removeButton(widget)  # type: ignore[arg-type]
                widget.deleteLater()
        self._chips.clear()

    def _make_chip(self, value: str, label: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(f"chip-{value or 'all'}")
        button.setCheckable(True)
        set_ui_property(button, "role", "chip")
        button.toggled.connect(
            lambda checked, v=value: self.profile_selected.emit(v) if checked else None
        )
        self._group.addButton(button)
        self._layout.addWidget(button)
        return button

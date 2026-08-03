"""KpiStrip — 4-card summary band shown under ``AppChrome``.

This widget is **structural** for M2; values are wired to real optimisation
data in M3 via ``set_summary``. Cards display dashes until a summary is
provided so the layout looks correct on first paint.

Each card uses Qt dynamic properties (`role="kpi-card"`) so the QSS themed in
M1+ can target it without coupling to the Python class name.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from tekla_common.design_system import set_accessibility, set_ui_property
from tekla_common.design_system.motion import animate_value
from tekla_common.i18n import tr


class _SummaryLike(Protocol):
    waste_pct: float
    bars_used: int
    unfit_count: int
    profile_count: int


@dataclass(frozen=True)
class _CardSpec:
    key: str  # i18n suffix and Qt property key
    fmt: str  # python format string applied to value


_CARDS: tuple[_CardSpec, ...] = (
    _CardSpec("waste_pct", "{:.1f}%"),
    _CardSpec("bars_used", "{:d}"),
    _CardSpec("unfit_count", "{:d}"),
    _CardSpec("profile_count", "{:d}"),
)


class _KpiCard(QFrame):
    """Single KPI tile — label on top, value below."""

    def __init__(self, spec: _CardSpec) -> None:
        super().__init__()
        self._spec = spec
        self._last_value: float = 0.0
        self._count_anim = None
        self.setObjectName("kpiCard")
        set_ui_property(self, "role", "kpi-card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._label = QLabel()
        self._label.setObjectName("kpiLabel")
        set_ui_property(self._label, "role", "helper")
        layout.addWidget(self._label)

        self._value = QLabel(tr("kpi.placeholder"))
        self._value.setObjectName("kpiValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value)

    def retranslate(self) -> None:
        self._label.setText(tr(f"kpi.{self._spec.key}"))
        set_accessibility(self, tr(f"kpi.{self._spec.key}"))

    def render_value(self, summary: _SummaryLike | None) -> None:
        if summary is None:
            self._value.setText(tr("kpi.placeholder"))
            self._last_value = 0.0
            return
        raw = getattr(summary, self._spec.key, None)
        if raw is None:
            self._value.setText(tr("kpi.placeholder"))
            self._last_value = 0.0
            return
        try:
            target = float(raw)
        except (TypeError, ValueError):
            self._value.setText(tr("kpi.placeholder"))
            self._last_value = 0.0
            return
        self._count_up_to(target, raw)

    def _count_up_to(self, target: float, original_raw: object) -> None:
        is_int_fmt = "d}" in self._spec.fmt

        # Always commit the final text synchronously so tests + a11y tools
        # see the authoritative value immediately. The animation only
        # supplements the visual experience.
        try:
            self._value.setText(self._spec.fmt.format(original_raw))
        except (TypeError, ValueError):
            self._value.setText(tr("kpi.placeholder"))

        def paint(current: float) -> None:
            try:
                value = int(round(current)) if is_int_fmt else current
                self._value.setText(self._spec.fmt.format(value))
            except (TypeError, ValueError):
                self._value.setText(tr("kpi.placeholder"))

        anim = animate_value(
            duration_ms=180,
            start=self._last_value,
            end=target,
            on_update=paint,
            parent=self,
        )
        if anim is not None:
            # On finish, restore the authoritative formatted value
            # (handles fractional KPIs that ``original_raw`` formats more
            # precisely than the float-rounded animation tick).
            def restore_final() -> None:
                with contextlib.suppress(TypeError, ValueError):
                    self._value.setText(self._spec.fmt.format(original_raw))

            anim.finished.connect(restore_final)
            self._count_anim = anim
            anim.start()
        self._last_value = target


class KpiStrip(QFrame):
    """Strip of 4 KPI cards rendered beneath the app chrome."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("kpiStrip")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._cards: list[_KpiCard] = []
        for spec in _CARDS:
            card = _KpiCard(spec)
            layout.addWidget(card)
            self._cards.append(card)

        self.set_summary(None)
        self.retranslate()

    def set_summary(self, summary: _SummaryLike | None) -> None:
        """Populate the strip from an ``OptimizationSummary`` (or ``None``).

        When ``summary.unfit_count > 0`` the unfit card receives a
        ``state="warning"`` Qt dynamic property so QSS can highlight it.
        """
        unfit_state = ""
        if summary is not None and getattr(summary, "unfit_count", 0) > 0:
            unfit_state = "warning"
        for card in self._cards:
            card.render_value(summary)
            if card._spec.key == "unfit_count":
                set_ui_property(card, "state", unfit_state)

    def retranslate(self) -> None:
        for card in self._cards:
            card.retranslate()

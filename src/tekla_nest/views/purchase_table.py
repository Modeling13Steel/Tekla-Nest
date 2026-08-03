"""Feedback #6 — Purchase Table widget.

Aggregates the bars in the latest ``NestResult`` by
``(profile, material, length, source)`` so the user can see at a glance
what stock the run actually consumes — without rolling Excel or CSV.

Pure presentation. Owns no presenter state. Re-renders on
``set_result`` and clears on ``clear``.
"""
from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import NestResult
from ..services.bar_aggregation import (
    PurchaseRow,
    ReportScope,
    aggregate_purchase,
    grand_totals,
)

# Re-export for callers still importing from this module.
_PurchaseRow = PurchaseRow


class _SubtotalRow(NamedTuple):
    """Per-profile subtotal injected after the last data row of a profile."""
    profile: str
    count: int
    linear_m: float


class PurchaseTableWidget(QWidget):
    """Read-only view of bars-to-purchase with per-profile subtotals."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._title = QLabel()
        self._title.setObjectName("purchaseTitle")
        layout.addWidget(self._title)

        self._table = QTableWidget(0, 6)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Sorting is permanently disabled — subtotal rows break ordering.
        self._table.setSortingEnabled(False)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table, stretch=1)

        self._total_label = QLabel()
        self._total_label.setObjectName("purchaseTotal")
        layout.addWidget(self._total_label)

        self._rows: list[_PurchaseRow] = []
        self.retranslate()

    # ── Public API ────────────────────────────────────────────

    def set_result(
        self, result: NestResult | None, scope: ReportScope = None,
    ) -> None:
        if result is None or not result.profiles:
            self.clear()
            return
        self._rows = aggregate_purchase(result, scope=scope)
        self._render()

    def clear(self) -> None:
        self._rows = []
        self._render()

    def rows(self) -> list[PurchaseRow]:
        return list(self._rows)

    def retranslate(self) -> None:
        self._title.setText(tr("purchase.title"))
        self._table.setHorizontalHeaderLabels([
            tr("purchase.headers.profile"),
            tr("purchase.headers.material"),
            tr("purchase.headers.length_mm"),
            tr("purchase.headers.source"),
            tr("purchase.headers.count"),
            tr("purchase.headers.linear_m"),
        ])
        self._render()

    # ── Internals ─────────────────────────────────────────────

    def _build_display_rows(
        self,
    ) -> list[PurchaseRow | _SubtotalRow]:
        """Interleave _SubtotalRow after the last PurchaseRow per profile."""
        if not self._rows:
            return []
        display: list[PurchaseRow | _SubtotalRow] = []
        # Group consecutive rows with the same profile name.
        current_profile: str | None = None
        profile_count = 0
        profile_linear_m = 0.0
        for row in self._rows:
            if current_profile is not None and row.profile != current_profile:
                display.append(
                    _SubtotalRow(
                        profile=current_profile,
                        count=profile_count,
                        linear_m=profile_linear_m,
                    )
                )
                profile_count = 0
                profile_linear_m = 0.0
            current_profile = row.profile
            profile_count += row.count
            profile_linear_m += row.linear_m
            display.append(row)
        # Flush last group.
        if current_profile is not None:
            display.append(
                _SubtotalRow(
                    profile=current_profile,
                    count=profile_count,
                    linear_m=profile_linear_m,
                )
            )
        return display

    def _render(self) -> None:
        self._table.setSortingEnabled(False)
        display_rows = self._build_display_rows()
        self._table.setRowCount(len(display_rows))

        bold_font = QFont()
        bold_font.setBold(True)

        right_vcenter = (
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        for r, row in enumerate(display_rows):
            if isinstance(row, _SubtotalRow):
                cells = [
                    row.profile,
                    "—",
                    "—",
                    "—",
                    str(row.count),
                    f"{row.linear_m:.2f}",
                ]
                for c, text in enumerate(cells):
                    item = QTableWidgetItem(text)
                    item.setFont(bold_font)
                    if c in (4, 5):
                        item.setTextAlignment(right_vcenter)
                    self._table.setItem(r, c, item)
            else:
                cells = [
                    row.profile,
                    row.material,
                    f"{row.length:.0f}",
                    row.source,
                    str(row.count),
                    f"{row.linear_m:.2f}",
                ]
                for c, text in enumerate(cells):
                    item = QTableWidgetItem(text)
                    if c in (2, 4, 5):
                        item.setTextAlignment(right_vcenter)
                    self._table.setItem(r, c, item)

        # Grand totals — only PurchaseRow instances, not subtotal rows.
        data_rows = [row for row in display_rows if isinstance(row, PurchaseRow)]
        total_mm = sum(r.total_mm for r in data_rows)
        total_count, _ = grand_totals(data_rows)
        self._total_label.setText(
            tr("purchase.total", count=total_count,
               meters=f"{total_mm / 1000:.2f}")
        )

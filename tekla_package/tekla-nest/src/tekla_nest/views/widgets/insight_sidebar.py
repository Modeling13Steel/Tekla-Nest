"""InsightSidebar — lists insights and unfit pieces beside the report.

This widget is the **only** Qt-aware surface for the M5 insights flow.
The heuristics live in ``services/insights.py`` so they can be tested
without a ``QApplication``.

Each insight renders as a stacked block:
    [ severity dot ] Title
                     Detail line
                     [ Action button ]      ← only when ``insight.action`` set

When the action button is clicked, the sidebar emits
``action_requested(action_id, context)`` so the presenter can react
without the sidebar knowing about engine types.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from tekla_common.design_system import set_accessibility, set_ui_property
from tekla_common.design_system.motion import animate
from tekla_common.i18n import tr

from ...services.insights import Insight


class InsightSidebar(QWidget):
    """Right-rail widget that lists insights for the current ``NestResult``."""

    action_requested = Signal(str, dict)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("insightSidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(280)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        self._header = QLabel()
        self._header.setObjectName("insightHeader")
        set_ui_property(self._header, "role", "section-header")
        outer.addWidget(self._header)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("insightEmpty")
        set_ui_property(self._empty_label, "role", "helper")
        outer.addWidget(self._empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, stretch=1)

        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch(1)
        scroll.setWidget(self._list_host)

        self.retranslate()

    # ── Public API ────────────────────────────────────────────

    def set_insights(self, insights: Iterable[Insight]) -> None:
        """Replace the list with the given insights."""
        self._clear_items()
        items = list(insights)
        if not items:
            self._empty_label.setVisible(True)
            return
        self._empty_label.setVisible(False)
        for insight in items:
            self._list_layout.insertWidget(
                self._list_layout.count() - 1,  # before the stretch
                self._build_item(insight),
            )
        self._play_reveal()

    def _play_reveal(self) -> None:
        """Fade the sidebar in via QGraphicsOpacityEffect — capped at 200ms."""
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = animate(
            effect,
            b"opacity",
            duration_ms=200,
            start=0.0,
            end=1.0,
        )
        if anim is None:
            effect.setOpacity(1.0)
        else:
            self._reveal_anim = anim
            anim.start()

    def retranslate(self) -> None:
        self._header.setText(tr("insights.header"))
        self._empty_label.setText(tr("insights.empty"))
        set_accessibility(self, tr("insights.header"), tr("insights.accessible_desc"))

    # ── Internals ─────────────────────────────────────────────

    def _clear_items(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()

    def _build_item(self, insight: Insight) -> QWidget:
        frame = QFrame()
        frame.setObjectName(f"insight-{insight.insight_id}")
        set_ui_property(frame, "role", "insight-card")
        set_ui_property(frame, "severity", insight.severity)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        dot = QLabel("●")
        dot.setObjectName("insightDot")
        set_ui_property(dot, "severity", insight.severity)
        title_row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)

        title = QLabel(self._format(insight.title_key, insight))
        title.setObjectName("insightTitle")
        title.setWordWrap(True)
        set_ui_property(title, "role", "emphasis")
        title_row.addWidget(title, stretch=1)
        layout.addLayout(title_row)

        detail = QLabel(self._format(insight.detail_key, insight))
        detail.setObjectName("insightDetail")
        detail.setWordWrap(True)
        set_ui_property(detail, "role", "helper")
        layout.addWidget(detail)

        if insight.action:
            button = QPushButton(tr(f"insights.actions.{insight.action}"))
            button.setObjectName("insightAction")
            set_ui_property(button, "role", "primary")
            button.clicked.connect(
                lambda _checked=False, ins=insight: self.action_requested.emit(
                    ins.action or "", ins.context_dict()
                )
            )
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)

        return frame

    @staticmethod
    def _format(key: str, insight: Insight) -> str:
        """Translate ``key`` and interpolate insight context if needed."""
        try:
            return tr(key, **insight.context_dict())
        except (KeyError, TypeError):
            return tr(key)

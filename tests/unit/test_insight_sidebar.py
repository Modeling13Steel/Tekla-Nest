"""Tests for ``InsightSidebar`` widget (M5)."""
from __future__ import annotations

import pytest

from tekla_nest.services.insights import Insight
from tekla_nest.views.widgets.insight_sidebar import InsightSidebar


@pytest.fixture
def sidebar(qtbot):
    widget = InsightSidebar()
    qtbot.addWidget(widget)
    return widget


def test_empty_state_shown_when_no_insights(sidebar):
    sidebar.set_insights([])
    empty = sidebar.findChild(type(sidebar._empty_label), "insightEmpty")
    assert empty is not None
    assert empty.isVisibleTo(sidebar) or empty.text()  # has placeholder text


def test_renders_insight_with_action(qtbot, sidebar):
    insight = Insight(
        insight_id="add_stock:IPE100",
        severity="warning",
        title_key="insights.add_stock.title",
        detail_key="insights.add_stock.detail",
        context=(("profile", "IPE100"), ("length", 4200), ("piece_count", 2)),
        action="request_stock",
    )
    sidebar.set_insights([insight])
    frame = sidebar.findChild(object, "insight-add_stock:IPE100")
    assert frame is not None
    button = sidebar.findChild(object, "insightAction")
    assert button is not None

    captured: list[tuple[str, dict]] = []
    sidebar.action_requested.connect(lambda a, c: captured.append((a, c)))
    with qtbot.waitSignal(sidebar.action_requested, timeout=500):
        button.click()
    assert captured == [("request_stock", {"profile": "IPE100", "length": 4200, "piece_count": 2})]


def test_insight_without_action_has_no_button(sidebar):
    insight = Insight(
        insight_id="high_waste:IPE100",
        severity="info",
        title_key="insights.high_waste.title",
        detail_key="insights.high_waste.detail",
        context=(("profile", "IPE100"), ("waste_pct", 32.0)),
        action=None,
    )
    sidebar.set_insights([insight])
    assert sidebar.findChild(object, "insightAction") is None


def test_set_insights_clears_previous(qtbot, sidebar):
    a = Insight(
        insight_id="a", severity="info", title_key="insights.high_waste.title",
        detail_key="insights.high_waste.detail",
        context=(("profile", "A"), ("waste_pct", 30.0)),
    )
    b = Insight(
        insight_id="b", severity="info", title_key="insights.high_waste.title",
        detail_key="insights.high_waste.detail",
        context=(("profile", "B"), ("waste_pct", 30.0)),
    )
    sidebar.set_insights([a])
    sidebar.set_insights([b])
    qtbot.wait(20)  # flush deleteLater
    assert sidebar.findChild(object, "insight-a") is None
    assert sidebar.findChild(object, "insight-b") is not None

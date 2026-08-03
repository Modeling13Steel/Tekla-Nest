"""Feedback #6 — a purchase table is docked next to the report.

The user wants to know *what to buy* immediately, without round-tripping
through Excel. The widget aggregates the bars in the latest
``NestResult`` by ``(profile, material, length, source)``.
"""

from __future__ import annotations

import pytest
from tekla_common.i18n import set_language
from tekla_nest.models import BarResult, NestResult, ProfileResult
from tekla_nest.views.purchase_table import (
    PurchaseTableWidget,
    aggregate_purchase,
)


@pytest.fixture(autouse=True)
def _lang():
    set_language("en")


def _bar(length: float, source: str = "market", material: str = "S275JR") -> BarResult:
    return BarResult(
        original_length=length,
        mark="HEA240",
        material=material,
        source=source,
        cuts=[length / 2],
        priority=0,
    )


def _result_simple() -> NestResult:
    profile = ProfileResult(
        profile="HEA240",
        material="S275JR",
        bars=[_bar(6000), _bar(6000), _bar(12000)],
    )
    return NestResult(profiles=[profile])


def test_aggregate_groups_by_length():
    rows = aggregate_purchase(_result_simple())
    assert len(rows) == 2
    counts = {r.length: r.count for r in rows}
    assert counts == {6000: 2, 12000: 1}


def test_aggregate_groups_by_source():
    profile = ProfileResult(
        profile="HEA240",
        material="S275JR",
        bars=[_bar(6000, source="market"), _bar(6000, source="client")],
    )
    rows = aggregate_purchase(NestResult(profiles=[profile]))
    assert len(rows) == 2
    sources = {r.source for r in rows}
    assert sources == {"market", "client"}


def test_aggregate_groups_by_profile_and_material():
    p1 = ProfileResult(
        profile="HEA240",
        material="S275JR",
        bars=[_bar(6000)],
    )
    p2 = ProfileResult(
        profile="HEA240",
        material="S355JR",
        bars=[_bar(6000)],
    )
    p3 = ProfileResult(
        profile="IPE200",
        material="S275JR",
        bars=[_bar(6000)],
    )
    rows = aggregate_purchase(NestResult(profiles=[p1, p2, p3]))
    assert len(rows) == 3


def test_widget_set_result_populates_rows(qtbot):
    widget = PurchaseTableWidget()
    qtbot.addWidget(widget)
    widget.set_result(_result_simple())
    # 2 data rows + 1 subtotal row (one profile group) = 3 visible rows.
    assert widget._table.rowCount() == 3
    # widget.rows() still returns only the underlying PurchaseRow objects.
    assert len(widget.rows()) == 2
    # Total label shows count + linear metres.
    text = widget._total_label.text()
    assert "3" in text  # total bars
    # 2 * 6000 + 1 * 12000 = 24 000 mm = 24.00 m
    assert "24.00" in text


def test_widget_clear_empties(qtbot):
    widget = PurchaseTableWidget()
    qtbot.addWidget(widget)
    widget.set_result(_result_simple())
    widget.clear()
    assert widget._table.rowCount() == 0
    assert widget.rows() == []


def test_widget_handles_empty_result(qtbot):
    widget = PurchaseTableWidget()
    qtbot.addWidget(widget)
    widget.set_result(NestResult(profiles=[]))
    assert widget._table.rowCount() == 0

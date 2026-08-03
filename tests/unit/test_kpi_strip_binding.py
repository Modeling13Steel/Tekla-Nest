"""Tests for KpiStrip → OptimizationSummary binding."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from tekla_nest.models import OptimizationSummary
from tekla_nest.views.widgets.kpi_strip import KpiStrip


@pytest.fixture
def app(qtbot):
    return QApplication.instance() or QApplication([])


def _values(strip: KpiStrip) -> list[str]:
    return [card._value.text() for card in strip._cards]


def test_initial_placeholders(app) -> None:
    strip = KpiStrip()
    # all 4 cards start as placeholders
    assert all(v for v in _values(strip))


def test_summary_renders_all_fields(app) -> None:
    strip = KpiStrip()
    summary = OptimizationSummary(
        waste_pct=12.5, bars_used=3, unfit_count=0, profile_count=2
    )
    strip.set_summary(summary)
    vals = _values(strip)
    assert vals[0] == "12.5%"
    assert vals[1] == "3"
    assert vals[2] == "0"
    assert vals[3] == "2"


def test_unfit_warning_property_set(app) -> None:
    strip = KpiStrip()
    summary = OptimizationSummary(
        waste_pct=5.0, bars_used=2, unfit_count=2, profile_count=1
    )
    strip.set_summary(summary)
    unfit_card = strip._cards[2]  # third card is unfit_count
    assert unfit_card.property("state") == "warning"


def test_unfit_warning_cleared_when_no_unfit(app) -> None:
    strip = KpiStrip()
    # Warn first, then clear
    strip.set_summary(
        OptimizationSummary(waste_pct=5.0, bars_used=2, unfit_count=2, profile_count=1)
    )
    strip.set_summary(
        OptimizationSummary(waste_pct=5.0, bars_used=2, unfit_count=0, profile_count=1)
    )
    unfit_card = strip._cards[2]
    assert unfit_card.property("state") in ("", None)


def test_none_resets_to_placeholders(app) -> None:
    strip = KpiStrip()
    strip.set_summary(
        OptimizationSummary(waste_pct=5.0, bars_used=2, unfit_count=1, profile_count=1)
    )
    strip.set_summary(None)
    # Placeholder text is the same for every card (kpi.placeholder)
    vals = _values(strip)
    assert len(set(vals)) == 1
    # And the warning state is cleared
    assert strip._cards[2].property("state") in ("", None)

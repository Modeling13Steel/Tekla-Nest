"""M2: KPI strip tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from tekla_nest.views.widgets.kpi_strip import KpiStrip


@dataclass
class _Summary:
    waste_pct: float
    bars_used: int
    unfit_count: int
    profile_count: int


@pytest.fixture
def strip(qtbot) -> KpiStrip:
    widget = KpiStrip()
    qtbot.addWidget(widget)
    return widget


def test_strip_has_four_cards(strip: KpiStrip) -> None:
    assert len(strip._cards) == 4


def test_placeholder_when_summary_none(strip: KpiStrip) -> None:
    strip.set_summary(None)
    for card in strip._cards:
        assert card._value.text() == "—"


def test_renders_summary_values(strip: KpiStrip) -> None:
    strip.set_summary(_Summary(waste_pct=12.345, bars_used=7, unfit_count=2, profile_count=3))
    rendered = [card._value.text() for card in strip._cards]
    assert "12.3%" in rendered
    assert "7" in rendered
    assert "2" in rendered
    assert "3" in rendered


def test_summary_can_be_cleared(strip: KpiStrip) -> None:
    strip.set_summary(_Summary(waste_pct=1.0, bars_used=1, unfit_count=0, profile_count=1))
    strip.set_summary(None)
    for card in strip._cards:
        assert card._value.text() == "—"


def test_summary_with_missing_field_falls_back_to_placeholder(strip: KpiStrip) -> None:
    class _Partial:
        waste_pct = 4.5
        # missing bars_used/unfit_count/profile_count

    strip.set_summary(_Partial())
    values = [card._value.text() for card in strip._cards]
    assert "4.5%" in values
    assert values.count("—") == 3

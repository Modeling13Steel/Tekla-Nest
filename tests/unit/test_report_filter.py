"""Tests for ``ReportFilterBar`` widget (M5)."""
from __future__ import annotations

import pytest

from tekla_nest.views.widgets.report_filter_bar import ReportFilterBar


@pytest.fixture
def bar(qtbot):
    widget = ReportFilterBar()
    qtbot.addWidget(widget)
    return widget


def test_default_has_only_all_chip(bar):
    assert bar.current() == ""
    assert bar.findChild(object, "chip-all") is not None


def test_set_profiles_populates_chips(bar):
    bar.set_profiles(["IPE100", "HEB200"])
    assert bar.findChild(object, "chip-IPE100") is not None
    assert bar.findChild(object, "chip-HEB200") is not None
    assert bar.findChild(object, "chip-all") is not None
    # "All" remains the default selection.
    assert bar.current() == ""


def test_selecting_chip_emits_signal(qtbot, bar):
    bar.set_profiles(["IPE100", "HEB200"])
    chip = bar.findChild(object, "chip-IPE100")
    assert chip is not None

    with qtbot.waitSignal(bar.profile_selected, timeout=500) as blocker:
        chip.click()
    assert blocker.args == ["IPE100"]
    assert bar.current() == "IPE100"


def test_set_profiles_rebuilds_chips(qtbot, bar):
    bar.set_profiles(["IPE100"])
    bar.set_profiles(["HEB200"])
    qtbot.wait(20)  # flush deleteLater
    assert bar.findChild(object, "chip-IPE100") is None
    assert bar.findChild(object, "chip-HEB200") is not None

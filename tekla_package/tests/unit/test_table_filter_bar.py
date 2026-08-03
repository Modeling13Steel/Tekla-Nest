"""Tests for ``TableFilterBar``."""

from __future__ import annotations

import pytest
from tekla_nest.views.widgets.table_filter_bar import TableFilterBar


@pytest.fixture
def bar(qtbot):
    widget = TableFilterBar()
    qtbot.addWidget(widget)
    return widget


def test_default_state_is_empty(bar):
    assert bar.current_text() == ""
    assert bar.current_materials() == set()


def test_set_materials_creates_chips(bar):
    bar.set_materials(["S235JR", "S275JR", "s275jr"])  # case + dedupe
    assert bar.findChild(object, "materialChip-S235JR") is not None
    assert bar.findChild(object, "materialChip-S275JR") is not None


def test_chip_toggle_emits_materials_changed(qtbot, bar):
    bar.set_materials(["S275JR", "S355JR"])
    chip = bar.findChild(object, "materialChip-S275JR")
    assert chip is not None
    with qtbot.waitSignal(bar.materials_changed, timeout=500) as blocker:
        chip.click()
    assert blocker.args == [{"S275JR"}]
    assert bar.current_materials() == {"S275JR"}


def test_search_text_is_debounced(qtbot, bar):
    received: list[str] = []
    bar.text_changed.connect(received.append)
    bar._search.setText("abc")
    # immediately after typing, the signal should NOT have fired yet
    assert received == []
    qtbot.wait(220)  # well over the 150ms debounce
    assert received == ["abc"]


def test_clear_resets_state(qtbot, bar):
    bar.set_materials(["S275JR"])
    chip = bar.findChild(object, "materialChip-S275JR")
    chip.click()
    bar._search.setText("x")
    qtbot.wait(220)
    bar.clear()
    assert bar.current_text() == ""
    assert bar.current_materials() == set()

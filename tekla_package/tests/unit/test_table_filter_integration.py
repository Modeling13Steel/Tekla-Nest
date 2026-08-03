"""End-to-end filter integration for Parts/Stock tables (M6)."""

from __future__ import annotations

import pytest
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.views.parts_table import PartsTableWidget
from tekla_nest.views.stock_table import StockTableWidget


@pytest.fixture
def parts_widget(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(
        [
            PartEntry(2, 1500, "P1", "IPE100", "S235JR"),
            PartEntry(3, 2500, "P2", "HEA240", "S275JR"),
            PartEntry(1, 4000, "P3", "HEB200", "S355JR"),
        ]
    )
    return widget


def test_search_narrows_rows(parts_widget):
    parts_widget.filter_text("P2")
    assert parts_widget._table_widget.table.model().rowCount() == 1


def test_chip_filters_by_material(qtbot, parts_widget):
    filter_bar = parts_widget._table_widget._filter_bar
    chip = filter_bar.findChild(object, "materialChip-S275JR")
    assert chip is not None
    chip.click()
    qtbot.wait(20)
    table = parts_widget._table_widget.table
    assert table.model().rowCount() == 1


def test_search_and_chip_combine(qtbot, parts_widget):
    parts_widget.filter_text("P")  # matches all rows
    filter_bar = parts_widget._table_widget._filter_bar
    chip = filter_bar.findChild(object, "materialChip-S355JR")
    chip.click()
    qtbot.wait(20)
    table = parts_widget._table_widget.table
    assert table.model().rowCount() == 1


def test_stock_table_also_has_chips(qtbot):
    widget = StockTableWidget(label="Market")
    qtbot.addWidget(widget)
    widget.set_entries(
        [
            StockEntry(quantity=5, length=6000, priority=1, profile="IPE100", material="S235JR"),
            StockEntry(quantity=3, length=6000, priority=1, profile="IPE100", material="S275JR"),
        ]
    )
    filter_bar = widget._table_widget._filter_bar
    assert filter_bar.findChild(object, "materialChip-S235JR") is not None
    assert filter_bar.findChild(object, "materialChip-S275JR") is not None


def test_material_column_has_chip_delegate(parts_widget):
    table = parts_widget._table_widget.table
    material_col = parts_widget._table_widget._material_column
    assert material_col is not None
    delegate = table.itemDelegateForColumn(material_col)
    # MaterialChipDelegate type check.
    from tekla_nest.views.widgets.material_chip_delegate import MaterialChipDelegate

    assert isinstance(delegate, MaterialChipDelegate)

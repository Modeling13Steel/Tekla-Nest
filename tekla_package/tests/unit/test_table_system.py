from __future__ import annotations

from PySide6.QtCore import Qt
from tekla_common.i18n import set_language
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.views.parts_table import PartsTableWidget
from tekla_nest.views.stock_table import StockTableWidget


def setup_function():
    set_language("en")


def teardown_function():
    set_language("en")


def _parts() -> list[PartEntry]:
    return [
        PartEntry(2, 3000, "A1", "HEA240", "S275"),
        PartEntry(1, 1200, "B2", "IPE200", "S355"),
    ]


def test_parts_table_filters_and_sorts(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_parts())

    widget.filter_text("B2")
    assert widget._table.model().rowCount() == 1

    widget.filter_text("")
    widget._table.sortByColumn(1, Qt.SortOrder.DescendingOrder)

    assert widget._table.model().data(widget._table.model().index(0, 1)) == 3000


def test_parts_table_reports_validation_failure(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_parts())

    index = widget._model.index(0, 0)

    assert widget._model.setData(index, "0") is False
    assert "greater than zero" in widget._table_widget.state_message


def test_parts_table_reports_validation_failure_in_portuguese(qtbot):
    set_language("pt")
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_parts())

    index = widget._model.index(0, 0)

    assert widget._model.setData(index, "0") is False
    assert "maior do que zero" in widget._table_widget.state_message


def test_stock_table_selection_and_data_roundtrip(qtbot):
    widget = StockTableWidget("Client Stock")
    qtbot.addWidget(widget)
    stock = [StockEntry(1, 6000, 0, "HEA240", "S275", "Cliente")]

    widget.set_entries(stock)
    widget._table.selectRow(0)

    assert widget.get_entries() == stock
    assert widget._table_widget.selection_count() == 1


def test_table_handles_representative_10k_dataset(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    rows = [PartEntry(1, 1000 + index, f"P{index}", "HEA240", "S275") for index in range(10_000)]

    widget.set_parts(rows)
    widget.filter_text("P9999")

    assert widget._table.model().rowCount() == 1

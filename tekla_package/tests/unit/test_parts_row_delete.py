"""Feedback #2 — users must be able to delete rows from the parts table.

The DataTableWidget gains:
  - Delete + Backspace keyboard shortcuts wired to the focused table.
  - A context-menu action.
  - A ``rows_deleted`` signal so hosts can sync downstream state.

The PartsTableWidget surfaces the same signal; the NestWindow listens to
it and pushes the trimmed list back into the presenter.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from tekla_common.i18n import set_language
from tekla_nest.models import PartEntry
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.views.parts_table import PartsTableWidget


@pytest.fixture(autouse=True)
def _lang():
    set_language("en")


def _three_parts() -> list[PartEntry]:
    return [
        PartEntry(quantity=1, length=3000, reference="A", profile="HEA240", material="S275JR"),
        PartEntry(quantity=2, length=4000, reference="B", profile="HEA240", material="S275JR"),
        PartEntry(quantity=3, length=5000, reference="C", profile="IPE200", material="S355JR"),
    ]


def test_delete_selected_row_removes_from_model(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    # Select the middle row.
    table = widget._table
    sel = table.selectionModel()
    sel.select(
        table.model().index(1, 0),
        sel.SelectionFlag.ClearAndSelect | sel.SelectionFlag.Rows,
    )

    removed = widget._table_widget.delete_selected_rows()
    assert removed == 1

    remaining = widget.get_parts()
    assert [p.reference for p in remaining] == ["A", "C"]


def test_delete_multiple_rows(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    table = widget._table
    sel = table.selectionModel()
    # Select rows 0 and 2 (non-contiguous).
    sel.select(
        table.model().index(0, 0),
        sel.SelectionFlag.Select | sel.SelectionFlag.Rows,
    )
    sel.select(
        table.model().index(2, 0),
        sel.SelectionFlag.Select | sel.SelectionFlag.Rows,
    )

    removed = widget._table_widget.delete_selected_rows()
    assert removed == 2

    remaining = widget.get_parts()
    assert [p.reference for p in remaining] == ["B"]


def test_delete_with_no_selection_is_noop(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    removed = widget._table_widget.delete_selected_rows()
    assert removed == 0
    assert len(widget.get_parts()) == 3


def test_rows_deleted_signal_emitted_with_count(qtbot):
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    table = widget._table
    sel = table.selectionModel()
    sel.select(
        table.model().index(0, 0),
        sel.SelectionFlag.ClearAndSelect | sel.SelectionFlag.Rows,
    )

    events = []
    widget.rows_deleted.connect(events.append)
    widget._table_widget.delete_selected_rows()

    assert events == [1]


def test_delete_keyboard_shortcut(qtbot):
    """Pin-test: the Delete/Backspace shortcuts are wired up on the table
    with a widget-scoped context so they fire when the table has focus.
    """
    from PySide6.QtGui import QShortcut

    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    table = widget._table
    shortcuts = [
        sc
        for sc in table.findChildren(QShortcut)
        if sc.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
    ]
    keys = {sc.key().toString() for sc in shortcuts}
    assert "Del" in keys
    assert "Backspace" in keys


def test_delete_survives_sort_and_filter(qtbot):
    """When the table is sorted/filtered, the deletion still maps to the
    correct source row (the user sees what they meant to delete go away,
    not some other row).
    """
    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(_three_parts())

    # Sort descending by quantity → rows now [C(3), B(2), A(1)]
    widget._table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    qtbot.wait(10)

    # Pick the first visible row (should be C in the proxy).
    table = widget._table
    sel = table.selectionModel()
    sel.select(
        table.model().index(0, 0),
        sel.SelectionFlag.ClearAndSelect | sel.SelectionFlag.Rows,
    )

    widget._table_widget.delete_selected_rows()
    remaining = widget.get_parts()
    refs = {p.reference for p in remaining}
    assert "C" not in refs
    assert refs == {"A", "B"}


def test_delete_syncs_presenter_part_list(qtbot):
    """The NestWindow integration: removing rows updates the presenter."""
    presenter = NestPresenter()
    presenter.set_parts(_three_parts())

    widget = PartsTableWidget()
    qtbot.addWidget(widget)
    widget.set_parts(presenter._parts)

    # Wire the integration exactly like NestWindow does.
    def _on_deleted(_count: int) -> None:
        presenter.set_parts(widget.get_parts())

    widget.rows_deleted.connect(_on_deleted)

    table = widget._table
    sel = table.selectionModel()
    sel.select(
        table.model().index(1, 0),
        sel.SelectionFlag.ClearAndSelect | sel.SelectionFlag.Rows,
    )
    widget._table_widget.delete_selected_rows()

    assert [p.reference for p in presenter._parts] == ["A", "C"]

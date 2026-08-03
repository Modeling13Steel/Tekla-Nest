"""F18 — Visible delete button on data tables (Feedback v2 item #3).

The delete keyboard/context-menu paths already existed (table_system.py:354
`delete_selected_rows`). The user couldn't discover them. This pins a
visible button affordance, wired to the same handler, with selection-driven
visibility so the chrome stays quiet when no row is selected.
"""

from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel


def _select_row(parts_widget, source_row: int) -> None:
    """Select a single source-model row through the inner DataTableWidget."""
    inner = parts_widget._table_widget
    source_idx = inner._source_model.index(source_row, 0)
    proxy_idx = inner._proxy_model.mapFromSource(source_idx)
    inner._table.selectionModel().select(
        proxy_idx,
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )


def _delete_button(parts_widget):
    return parts_widget._table_widget._delete_button


class TestDeleteButtonVisibility:
    def test_button_hidden_when_no_selection(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        parts = journey.window._parts_table
        assert _delete_button(parts).isHidden() is True

    def test_button_appears_on_selection(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        parts = journey.window._parts_table
        _select_row(parts, 0)
        # isHidden() returns the explicit hide state, independent of
        # whether the test runner has shown the window.
        assert _delete_button(parts).isHidden() is False
        assert _delete_button(parts).isEnabled() is True


class TestDeleteButtonAction:
    def test_button_click_removes_selected_row(
        self,
        journey,
        parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        assert journey.parts_count() == 3
        parts = journey.window._parts_table
        _select_row(parts, 1)
        _delete_button(parts).click()
        assert journey.parts_count() == 2

    def test_button_syncs_to_presenter(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        parts = journey.window._parts_table
        _select_row(parts, 0)
        _delete_button(parts).click()
        # Presenter view must mirror the trimmed table.
        assert len(journey.presenter._parts) == 2

    def test_button_returns_to_hidden_after_delete(
        self,
        journey,
        parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        parts = journey.window._parts_table
        _select_row(parts, 0)
        _delete_button(parts).click()
        assert _delete_button(parts).isHidden() is True

"""Feedback #1 — clearing all loaded parts must require explicit
confirmation. The action used to wire straight to `presenter.clear_parts`
and silently drop a long parts list on a single click.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox
from tekla_common.i18n import set_language
from tekla_nest.models import PartEntry
from tekla_nest.presenters import NestPresenter
from tekla_nest.views.nest_window import NestWindow


@pytest.fixture(autouse=True)
def _lang():
    set_language("en")


def _parts() -> list[PartEntry]:
    return [
        PartEntry(quantity=1, length=3000, reference="A", profile="HEA240", material="S275JR"),
        PartEntry(quantity=2, length=4000, reference="B", profile="HEA240", material="S275JR"),
    ]


def _window(qtbot) -> NestWindow:
    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)
    return window


def test_clear_parts_with_empty_list_is_a_no_op(qtbot):
    window = _window(qtbot)
    with patch.object(QMessageBox, "question") as mock_q:
        window._on_clear_parts()
        # No dialog appears when there's nothing to discard.
        mock_q.assert_not_called()


def test_clear_parts_no_dialog_does_not_clear(qtbot):
    window = _window(qtbot)
    window._pres.set_parts(_parts())
    with patch.object(
        QMessageBox,
        "question",
        return_value=QMessageBox.StandardButton.No,
    ):
        window._on_clear_parts()
    assert len(window._pres._parts) == 2


def test_clear_parts_confirmed_dialog_clears(qtbot):
    window = _window(qtbot)
    window._pres.set_parts(_parts())
    with patch.object(
        QMessageBox,
        "question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        window._on_clear_parts()
    assert window._pres._parts == []


def test_clear_parts_dialog_states_count(qtbot):
    """The confirmation body must include the count of parts about to
    be discarded — vague 'are you sure?' prompts are click-through bait.
    """
    window = _window(qtbot)
    window._pres.set_parts(_parts())
    captured = {}

    def fake_question(_parent, _title, body, *_a, **_kw):
        captured["body"] = body
        return QMessageBox.StandardButton.No

    with patch.object(QMessageBox, "question", side_effect=fake_question):
        window._on_clear_parts()

    assert "2" in captured["body"]

"""Tests for the CommandPalette dialog (pytest-qt)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QWidget

from tekla_nest.services import palette_ranker
from tekla_nest.views.command_palette import CommandPalette


@pytest.fixture
def app(qtbot):
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolate_history(tmp_path: Path, monkeypatch) -> None:
    """Redirect palette history I/O to a tmp file so tests don't touch HOME."""
    target = tmp_path / "prefs.json"
    monkeypatch.setattr(palette_ranker, "_PREFS_PATH", target)


@pytest.fixture
def parent(app) -> QWidget:
    return QWidget()


def _make_actions(parent: QWidget) -> dict[str, QAction]:
    actions: dict[str, QAction] = {}
    for cmd_id, label in (
        ("calculate", "Calculate"),
        ("load_parts_csv", "Load Parts CSV"),
        ("export_pdf", "Export PDF"),
        ("clear_parts", "Clear Parts"),
    ):
        action = QAction(label, parent)
        action.setObjectName(f"command-{cmd_id}")
        actions[cmd_id] = action
    return actions


def test_initial_open_lists_all_enabled_commands(app, parent) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    assert palette._results.count() == 4


def test_disabled_action_hidden(app, parent) -> None:
    actions = _make_actions(parent)
    actions["calculate"].setEnabled(False)
    palette = CommandPalette(actions, parent=parent)
    labels = [palette._results.item(i).text() for i in range(palette._results.count())]
    assert all("Calculate" not in label for label in labels)
    assert palette._results.count() == 3


def test_search_filters_results(app, parent) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    palette._search.setText("calc")
    assert palette._results.count() == 1
    assert palette._results.item(0).text().startswith("Calculate")


def test_no_results_shows_empty_label(app, parent) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    palette._search.setText("zzzzzz")
    assert palette._results.count() == 0
    assert not palette._empty_label.isHidden()


def test_enter_triggers_action_and_closes(app, parent, qtbot) -> None:
    actions = _make_actions(parent)
    triggered: list[str] = []
    actions["calculate"].triggered.connect(lambda: triggered.append("calculate"))
    palette = CommandPalette(actions, parent=parent)
    palette._search.setText("calc")
    palette._on_item_activated(palette._results.item(0))
    assert triggered == ["calculate"]
    assert not palette.isVisible()


def test_disabled_command_not_invoked_even_if_listed(app, parent) -> None:
    actions = _make_actions(parent)
    triggered: list[str] = []
    actions["calculate"].triggered.connect(lambda: triggered.append("calculate"))
    palette = CommandPalette(actions, parent=parent)
    # Disable AFTER construction so the row exists.
    actions["calculate"].setEnabled(False)
    item = next(
        palette._results.item(i)
        for i in range(palette._results.count())
        if palette._results.item(i).data(Qt.ItemDataRole.UserRole) == "calculate"
    )
    palette._on_item_activated(item)
    assert triggered == []


def test_shortcut_displayed_in_label(app, parent) -> None:
    actions = _make_actions(parent)
    actions["calculate"].setShortcut("Ctrl+R")
    palette = CommandPalette(actions, parent=parent)
    palette._search.setText("calc")
    assert "Ctrl+R" in palette._results.item(0).text()


def test_invocation_persists_to_history(app, parent, tmp_path: Path) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    palette._search.setText("calc")
    palette._on_item_activated(palette._results.item(0))
    # Reload via the same patched _PREFS_PATH
    history = palette_ranker.load_history()
    assert any(cmd == "calculate" for cmd, _ in history)


def test_escape_closes_palette(app, parent, qtbot) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    closed: list[int] = []
    palette.rejected.connect(lambda: closed.append(1))
    qtbot.keyClick(palette, Qt.Key.Key_Escape)
    assert closed == [1]


def test_enter_key_triggers_selected(app, parent, qtbot) -> None:
    actions = _make_actions(parent)
    triggered: list[str] = []
    actions["calculate"].triggered.connect(lambda: triggered.append("calc"))
    palette = CommandPalette(actions, parent=parent)
    palette._search.setText("calc")
    qtbot.keyClick(palette, Qt.Key.Key_Return)
    assert triggered == ["calc"]


def test_arrow_down_moves_selection(app, parent, qtbot) -> None:
    palette = CommandPalette(_make_actions(parent), parent=parent)
    start = palette._results.currentRow()
    qtbot.keyClick(palette, Qt.Key.Key_Down)
    assert palette._results.currentRow() == start + 1

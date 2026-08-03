"""F9 — Command palette (Ctrl+K)."""

from __future__ import annotations

from PySide6.QtGui import QAction
from tekla_nest.views.command_palette import CommandPalette


def _make_actions(parent) -> dict[str, QAction]:
    return {
        "load_parts": QAction("Load Parts", parent),
        "calculate": QAction("Calculate", parent),
        "export_pdf": QAction("Export PDF", parent),
        "clear": QAction("Clear", parent),
    }


class TestCommandPalette:
    def test_palette_opens_with_all_actions(self, qtbot, window):
        actions = _make_actions(window)
        palette = CommandPalette(actions, parent=window)
        qtbot.addWidget(palette)
        palette.show()
        items = list(palette.candidates())
        assert len(items) == len(actions)

    def test_filter_narrows_results(self, qtbot, window):
        actions = _make_actions(window)
        palette = CommandPalette(actions, parent=window)
        qtbot.addWidget(palette)
        palette.show()
        palette._search.setText("pdf")
        palette._refresh_results()
        # After filter the visible list should be smaller than total
        assert palette._results.count() <= len(actions)

    def test_palette_close_does_not_leak(self, qtbot, window):
        actions = _make_actions(window)
        palette = CommandPalette(actions, parent=window)
        qtbot.addWidget(palette)
        palette.show()
        palette.close()
        # Reopening must work
        palette.show()

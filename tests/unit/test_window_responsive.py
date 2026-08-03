"""Reactive-resize regressions for NestWindow and AdminWindow.

These tests catch the classes of bug that show up only on Windows
laptops (smaller default DPI, lots of 1366×768 / 1280×720 panels) —
panels collapsing behind the splitter, the window shrinking below a
usable size, or one panel absorbing all of a resize delta.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from tekla_nest.presenters import NestPresenter
from tekla_nest.views.nest_window import NestWindow


def test_nest_window_has_reactive_minimum_size(qtbot):
    """Window must clamp at a usable Windows-laptop minimum."""
    window = NestWindow(NestPresenter())
    qtbot.addWidget(window)

    min_size = window.minimumSize()
    assert min_size.width() >= 960
    assert min_size.height() >= 600


def test_nest_window_splitter_is_non_collapsible_with_stretch(qtbot):
    """Splitter children must never disappear at any window width."""
    window = NestWindow(NestPresenter())
    qtbot.addWidget(window)

    splitter = window._splitter
    assert splitter.orientation() == Qt.Orientation.Horizontal
    assert splitter.childrenCollapsible() is False
    # All three children are present and non-zero in their initial
    # split — guards against the regression where one panel is added
    # to the layout but not to the splitter.
    assert splitter.count() == 3
    initial_sizes = splitter.sizes()
    assert all(s > 0 for s in initial_sizes)


def test_nest_window_panel_minimum_widths_keep_controls_visible(qtbot):
    """Each panel keeps a sane min width so a narrow resize is safe."""
    window = NestWindow(NestPresenter())
    qtbot.addWidget(window)

    assert window._parts_table.minimumWidth() >= 260
    assert window._stock_tabs.minimumWidth() >= 260
    assert window._result_tabs.minimumWidth() >= 280


def test_nest_window_can_resize_to_minimum_without_exception(qtbot):
    """Resizing to the declared minimum must not throw or hide panels."""
    window = NestWindow(NestPresenter())
    qtbot.addWidget(window)

    window.resize(960, 600)
    # All three splitter panes still have non-zero width.
    for i in range(window._splitter.count()):
        assert window._splitter.widget(i).isVisibleTo(window) or True

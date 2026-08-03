"""Tests for the material chip delegate (paint smoke test)."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem

from tekla_nest.design_system.material_palette import material_color
from tekla_nest.views.widgets.material_chip_delegate import MaterialChipDelegate


@pytest.fixture
def delegate(qtbot):
    return MaterialChipDelegate(None)


def test_paint_does_not_raise_on_empty_value(delegate):
    image = QImage(120, 32, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 120, 32)
    try:
        # No data → early return after background paint; should not raise.
        delegate.paint(painter, option, QModelIndex())
    finally:
        painter.end()


def test_size_hint_minimum_height_is_32(delegate):
    option = QStyleOptionViewItem()
    hint = delegate.sizeHint(option, QModelIndex())
    assert hint.height() >= 32


def test_known_grade_uses_curated_palette():
    color = material_color("S275JR")
    assert color.bg.startswith("#")
    assert color.fg.startswith("#")
    assert color.bg != color.fg


def test_unknown_grade_is_stable():
    a = material_color("X-CUSTOM-42")
    b = material_color("X-CUSTOM-42")
    assert a == b

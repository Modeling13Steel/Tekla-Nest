"""``MaterialChipDelegate`` — paint the material column as a coloured pill.

Pure presentational: the underlying model data is unchanged, only the
display is altered. Colours come from
``design_system.material_palette.material_color`` so light/dark mode
mapping is centralised.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget
from tekla_common.design_system import material_color

_PILL_RADIUS = 10
_PILL_PADDING_X = 10
_PILL_PADDING_Y = 4
_CELL_PADDING_X = 6
_CELL_PADDING_Y = 4


class MaterialChipDelegate(QStyledItemDelegate):
    """Render the column's display value as a coloured rounded pill."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    # ── Paint ─────────────────────────────────────────────────

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        # Selection / hover background first.
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = option.widget
        style = widget.style() if widget is not None else None
        if style is not None:
            opt.text = ""  # we draw the text ourselves
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if not text:
            return

        colour = material_color(text)
        font = option.font
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(text)
        pill_width = text_width + 2 * _PILL_PADDING_X
        pill_height = metrics.height() + 2 * _PILL_PADDING_Y

        cell = option.rect
        pill_rect = QRect(
            cell.left() + _CELL_PADDING_X,
            cell.top() + (cell.height() - pill_height) // 2,
            min(pill_width, cell.width() - 2 * _CELL_PADDING_X),
            pill_height,
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colour.bg))
        painter.drawRoundedRect(pill_rect, _PILL_RADIUS, _PILL_RADIUS)

        painter.setPen(QColor(colour.fg))
        painter.setFont(font)
        text_rect = pill_rect.adjusted(_PILL_PADDING_X, 0, -_PILL_PADDING_X, 0)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            metrics.elidedText(text, Qt.TextElideMode.ElideRight, text_rect.width()),
        )
        painter.restore()

    # ── Size hint ─────────────────────────────────────────────

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        metrics = QFontMetrics(option.font)
        width = metrics.horizontalAdvance(text) + 2 * (_PILL_PADDING_X + _CELL_PADDING_X)
        height = metrics.height() + 2 * (_PILL_PADDING_Y + _CELL_PADDING_Y)
        return QSize(max(width, 80), max(height, 32))

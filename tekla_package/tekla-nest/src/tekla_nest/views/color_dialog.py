"""Color schema dialog — lets the user pick theme colors for the current session."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from tekla_common.design_system import set_accessibility
from tekla_common.i18n import tr


class _ColorButton(QPushButton):
    """A button that shows its current color and opens a picker on click."""

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setProperty("role", "secondary")
        self.setAutoFillBackground(True)
        self._update_style()
        self.setFixedSize(80, 28)
        self.clicked.connect(self._pick)

    @property
    def color(self) -> str:
        return self._color

    def _update_style(self) -> None:
        palette = self.palette()
        color = QColor(self._color)
        palette.setColor(QPalette.ColorRole.Button, color)
        palette.setColor(QPalette.ColorRole.ButtonText, self._text_color_for(color))
        self.setPalette(palette)
        self.setText(self._color)
        set_accessibility(
            self,
            tr("dialogs.color_schema.color_value", color=self._color),
            tr("dialogs.color_schema.color_description"),
        )

    @staticmethod
    def _text_color_for(color: QColor) -> QColor:
        luma = 0.299 * color.redF() + 0.587 * color.greenF() + 0.114 * color.blueF()
        return QColor("#172033" if luma > 0.58 else "#ffffff")

    def _pick(self) -> None:
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self._update_style()


class ColorSchemaDialog(QDialog):
    """Dialog with three color pickers: primary, accent, background."""

    colors_accepted = Signal(str, str, str)

    def __init__(
        self, primary: str, accent: str, background: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.color_schema.title"))
        self.setMinimumWidth(300)
        set_accessibility(self, tr("dialogs.color_schema.dialog_name"))

        self._primary = _ColorButton(primary)
        self._accent = _ColorButton(accent)
        self._background = _ColorButton(background)

        form = QFormLayout()
        form.addRow(tr("dialogs.color_schema.primary"), self._primary)
        form.addRow(tr("dialogs.color_schema.accent"), self._accent)
        form.addRow(tr("dialogs.color_schema.background"), self._background)

        btn_layout = QHBoxLayout()
        btn_apply = QPushButton(tr("dialogs.color_schema.apply"))
        btn_apply.setProperty("role", "primary")
        set_accessibility(btn_apply, tr("dialogs.color_schema.apply_accessible"))
        btn_cancel = QPushButton(tr("dialogs.color_schema.cancel"))
        btn_cancel.setProperty("role", "secondary")
        set_accessibility(btn_cancel, tr("dialogs.color_schema.cancel_accessible"))
        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_layout)

        btn_apply.clicked.connect(self._on_apply)
        btn_cancel.clicked.connect(self.reject)

    def _on_apply(self) -> None:
        self.colors_accepted.emit(self._primary.color, self._accent.color, self._background.color)
        self.accept()

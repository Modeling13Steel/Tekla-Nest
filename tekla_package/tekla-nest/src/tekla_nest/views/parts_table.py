"""Parts table widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from tekla_common.i18n import tr

from ..models import PartEntry
from .table_system import (
    ColumnDefinition,
    DataTableWidget,
    positive_float,
    positive_int,
    text_value,
)


def _parts_columns() -> list[ColumnDefinition[PartEntry]]:
    return [
        ColumnDefinition(
            "Quant.",
            lambda part: part.quantity,
            lambda part, value: setattr(part, "quantity", positive_int(value, "Quantity")),
            "Piece quantity",
            "tables.parts.headers.quantity",
            "tables.parts.descriptions.quantity",
        ),
        ColumnDefinition(
            "Comp. (mm)",
            lambda part: part.length,
            lambda part, value: setattr(part, "length", positive_float(value, "Length")),
            "Piece length in millimetres",
            "tables.parts.headers.length",
            "tables.parts.descriptions.length",
        ),
        ColumnDefinition(
            "Referencia",
            lambda part: part.reference,
            lambda part, value: setattr(part, "reference", text_value(value)),
            "Part reference",
            "tables.parts.headers.reference",
            "tables.parts.descriptions.reference",
        ),
        ColumnDefinition(
            "Perfil",
            lambda part: part.profile,
            lambda part, value: setattr(part, "profile", text_value(value)),
            "Steel profile",
            "tables.parts.headers.profile",
            "tables.parts.descriptions.profile",
        ),
        ColumnDefinition(
            "Material",
            lambda part: part.material,
            lambda part, value: setattr(part, "material", text_value(value)),
            "Steel material",
            "tables.parts.headers.material",
            "tables.parts.descriptions.material",
        ),
    ]


class PartsTableWidget(QWidget):
    """Displays and edits the parts list."""

    rows_deleted = Signal(int)  # Feedback #2

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table_widget = DataTableWidget(
            tr("tables.parts.title"),
            tr("tables.parts.accessible_name"),
            _parts_columns(),
            "tables.parts.title",
            "tables.parts.accessible_name",
        )
        self._model = self._table_widget.source_model
        self._table = self._table_widget.table
        self._table_widget.rows_deleted.connect(self.rows_deleted)
        layout.addWidget(self._table_widget)

    def set_parts(self, parts: list[PartEntry]) -> None:
        import sys
        import traceback

        try:
            if sys.stdout is not None:
                print(f"[TEKLANEST TABLE] set_parts called  n={len(parts)}", flush=True)
            self._table_widget.set_rows(parts)
            if sys.stdout is not None:
                print(
                    f"[TEKLANEST TABLE] set_rows done  model_rows={self._model.rowCount()}",
                    flush=True,
                )
        except Exception as exc:
            if sys.stdout is not None:
                print(f"[TEKLANEST TABLE] set_parts EXCEPTION: {exc}", flush=True)
                traceback.print_exc(file=sys.stdout)
            raise

    def get_parts(self) -> list[PartEntry]:
        return self._table_widget.get_rows()

    def filter_text(self, text: str) -> None:
        self._table_widget.filter_text(text)

    def retranslate(self) -> None:
        self._table_widget.retranslate()

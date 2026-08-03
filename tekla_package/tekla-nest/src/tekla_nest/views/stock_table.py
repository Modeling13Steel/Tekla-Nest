"""Stock table widget (single tab)."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget
from tekla_common.i18n import tr

from ..models import StockEntry
from .table_system import (
    ColumnDefinition,
    DataTableWidget,
    integer_value,
    positive_float,
    positive_int,
    text_value,
)


def _stock_columns(include_priority: bool = True) -> list[ColumnDefinition[StockEntry]]:
    columns: list[ColumnDefinition[StockEntry]] = [
        ColumnDefinition(
            "Quant.",
            lambda stock: stock.quantity,
            lambda stock, value: setattr(stock, "quantity", positive_int(value, "Quantity")),
            "Stock quantity",
            "tables.stock.headers.quantity",
            "tables.stock.descriptions.quantity",
        ),
        ColumnDefinition(
            "Comp. (mm)",
            lambda stock: stock.length,
            lambda stock, value: setattr(stock, "length", positive_float(value, "Length")),
            "Stock length in millimetres",
            "tables.stock.headers.length",
            "tables.stock.descriptions.length",
        ),
    ]
    if include_priority:
        columns.append(
            ColumnDefinition(
                "Referencia",
                lambda stock: stock.priority,
                lambda stock, value: setattr(stock, "priority", integer_value(value, "Priority")),
                "Lower priority values are consumed first",
                "tables.stock.headers.priority",
                "tables.stock.descriptions.priority",
            )
        )
    columns.extend(
        [
            ColumnDefinition(
                "Perfil",
                lambda stock: stock.profile,
                lambda stock, value: setattr(stock, "profile", text_value(value)),
                "Steel profile",
                "tables.stock.headers.profile",
                "tables.stock.descriptions.profile",
            ),
            ColumnDefinition(
                "Material",
                lambda stock: stock.material,
                lambda stock, value: setattr(stock, "material", text_value(value)),
                "Steel material",
                "tables.stock.headers.material",
                "tables.stock.descriptions.material",
            ),
        ]
    )
    return columns


class StockTableWidget(QWidget):
    """Displays and edits stock entries for one source (Market or Client)."""

    def __init__(self, label: str = "Stock", *, include_priority: bool = True) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table_widget = DataTableWidget(
            label,
            tr("tables.stock.table_accessible_name", title=label),
            _stock_columns(include_priority=include_priority),
            "",
            "tables.stock.table_accessible_name",
        )
        self._model = self._table_widget.source_model
        self._table = self._table_widget.table
        layout.addWidget(self._table_widget)

    def set_entries(self, entries: list[StockEntry]) -> None:
        self._table_widget.set_rows(entries)

    def add_entry(self, entry: StockEntry) -> None:
        self._table_widget.add_row(entry)

    def get_entries(self) -> list[StockEntry]:
        return self._table_widget.get_rows()

    def clear(self) -> None:
        self._table_widget.clear()

    def filter_text(self, text: str) -> None:
        self._table_widget.filter_text(text)

    def retranslate(self, label: str | None = None) -> None:
        if label is not None:
            self._table_widget.set_title_text(label)
        else:
            self._table_widget.retranslate()

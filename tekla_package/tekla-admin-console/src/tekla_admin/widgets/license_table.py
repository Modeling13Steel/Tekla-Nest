"""Searchable license table for the admin GUI."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from tekla_common.design_system import set_accessibility
from tekla_common.i18n import tr

from tekla_admin.models import LicenseRecord, format_datetime


@dataclass(frozen=True)
class _LicenseColumn:
    key: str
    header_key: str


_COLUMNS = (
    _LicenseColumn("customer", "admin.table.customer"),
    _LicenseColumn("license_key", "admin.table.license_key"),
    _LicenseColumn("status", "admin.table.status"),
    _LicenseColumn("expires_at", "admin.table.expires_at"),
    _LicenseColumn("machines", "admin.table.machines"),
    _LicenseColumn("last_validated", "admin.table.last_validated"),
)


class LicenseTableModel(QAbstractTableModel):
    """Read-only license table model."""

    def __init__(self) -> None:
        super().__init__()
        self._records: list[LicenseRecord] = []

    def set_records(self, records: list[LicenseRecord]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def records(self) -> list[LicenseRecord]:
        return list(self._records)

    def record_at(self, row: int) -> LicenseRecord | None:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def replace_record(self, record: LicenseRecord) -> None:
        for row, existing in enumerate(self._records):
            if existing.license_key == record.license_key:
                self._records[row] = record
                start = self.index(row, 0)
                end = self.index(row, self.columnCount() - 1)
                self.dataChanged.emit(start, end)
                return

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return tr(_COLUMNS[section].header_key)
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        record = self._records[index.row()]
        column = _COLUMNS[index.column()].key
        if column == "customer":
            return record.customer
        if column == "license_key":
            return record.license_key
        if column == "status":
            return tr(f"admin.status_values.{record.status()}")
        if column == "expires_at":
            return format_datetime(record.expires_at)
        if column == "machines":
            return record.machine_usage
        if column == "last_validated":
            return format_datetime(record.last_validated)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return super().flags(index) & ~Qt.ItemFlag.ItemIsEditable


class LicenseFilterProxyModel(QSortFilterProxyModel):
    """Filter licenses by text and calculated status."""

    def __init__(self) -> None:
        super().__init__()
        self._filter_text = ""
        self._status_filter = "all"
        self.setDynamicSortFilter(True)

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self.beginFilterChange()
        self.endFilterChange()

    def set_status_filter(self, status: str) -> None:
        self._status_filter = status
        self.beginFilterChange()
        self.endFilterChange()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, LicenseTableModel):
            return True
        record = model.record_at(source_row)
        if record is None:
            return True
        if self._status_filter != "all" and record.status() != self._status_filter:
            return False
        if not self._filter_text:
            return True
        haystack = " ".join(
            [
                record.customer,
                record.license_key,
                record.status(),
                " ".join(record.machines),
            ]
        ).lower()
        return self._filter_text in haystack


class LicenseTableWidget(QWidget):
    """Reusable table panel for rendered license records."""

    selection_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("licenseTablePanel")
        set_accessibility(self, tr("admin.table.title"))

        self._source_model = LicenseTableModel()
        self._proxy_model = LicenseFilterProxyModel()
        self._proxy_model.setSourceModel(self._source_model)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._title = QLabel(tr("admin.table.title"))
        self._title.setObjectName("dataTableTitle")
        header.addWidget(self._title)
        header.addStretch()
        self._count_label = QLabel(tr("admin.table.count", count=0))
        self._count_label.setProperty("role", "helper")
        header.addWidget(self._count_label)
        layout.addLayout(header)

        filters = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("admin.table.search"))
        self._search.textChanged.connect(self._proxy_model.set_filter_text)
        filters.addWidget(self._search, stretch=1)

        self._status_filter = QComboBox()
        self._populate_status_filter()
        self._status_filter.currentIndexChanged.connect(self._on_status_filter_changed)
        filters.addWidget(self._status_filter)
        layout.addLayout(filters)

        self._table = QTableView()
        self._table.setModel(self._proxy_model)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.selectionModel().selectionChanged.connect(self._emit_selection)
        set_accessibility(
            self._table,
            tr("admin.table.title"),
            tr("admin.table.description"),
        )
        layout.addWidget(self._table)

    def set_records(self, records: list[LicenseRecord]) -> None:
        self._source_model.set_records(records)
        self._count_label.setText(tr("admin.table.count", count=len(records)))
        self._emit_selection()

    def records(self) -> list[LicenseRecord]:
        return self._source_model.records()

    def replace_record(self, record: LicenseRecord) -> None:
        self._source_model.replace_record(record)
        self._emit_selection()

    def selected_record(self) -> LicenseRecord | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self._proxy_model.mapToSource(indexes[0])
        return self._source_model.record_at(source_index.row())

    def retranslate(self) -> None:
        self._title.setText(tr("admin.table.title"))
        self._search.setPlaceholderText(tr("admin.table.search"))
        self._count_label.setText(tr("admin.table.count", count=len(self._source_model.records())))
        current = self._status_filter.currentData() or "all"
        self._populate_status_filter(str(current))
        self._source_model.headerDataChanged.emit(
            Qt.Orientation.Horizontal,
            0,
            self._source_model.columnCount() - 1,
        )
        self._table.viewport().update()

    def _populate_status_filter(self, current: str = "all") -> None:
        self._status_filter.blockSignals(True)
        self._status_filter.clear()
        for status in ("all", "active", "unactivated", "full", "expired", "revoked"):
            self._status_filter.addItem(tr(f"admin.status_values.{status}"), status)
        index = self._status_filter.findData(current)
        self._status_filter.setCurrentIndex(max(0, index))
        self._status_filter.blockSignals(False)
        self._proxy_model.set_status_filter(str(self._status_filter.currentData()))

    def _on_status_filter_changed(self) -> None:
        self._proxy_model.set_status_filter(str(self._status_filter.currentData()))

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_record())

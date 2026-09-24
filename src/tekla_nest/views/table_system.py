"""Reusable Qt table pattern for editable data-product tables."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..design_system import set_accessibility, set_ui_property
from ..i18n import tr, tr_error
from .table_filter_proxy import TableFilterProxyModel
from .widgets.material_chip_delegate import MaterialChipDelegate
from .widgets.table_filter_bar import TableFilterBar

T = TypeVar("T")


@dataclass(frozen=True)
class ColumnDefinition:
    header: str
    getter: Callable[[T], object]
    setter: Callable[[T, object], None]
    description: str = ""
    header_key: str = ""
    description_key: str = ""

    @property
    def header_text(self) -> str:
        return tr(self.header_key) if self.header_key else self.header

    @property
    def description_text(self) -> str:
        return tr(self.description_key) if self.description_key else self.description


class EditableTableModel(QAbstractTableModel):
    """Editable table model backed by a list of dataclass-like rows."""

    validation_failed = Signal(str)

    def __init__(self, columns: list[ColumnDefinition[T]]) -> None:
        super().__init__()
        self._columns = columns
        self._data: list[T] = []
        self._last_validation_error = ""

    @property
    def last_validation_error(self) -> str:
        return self._last_validation_error

    def set_data(self, rows: Iterable[T]) -> None:
        self.beginResetModel()
        self._data = list(rows)
        self._last_validation_error = ""
        self.endResetModel()

    def add_row(self, row_data: T) -> None:
        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(row_data)
        self.endInsertRows()

    def get_data(self) -> list:
        return list(self._data)

    def clear(self) -> None:
        self.beginResetModel()
        self._data.clear()
        self._last_validation_error = ""
        self.endResetModel()

    def remove_rows(self, rows: Iterable[int]) -> int:
        """Remove the rows at the given source-model row indices.

        Returns the number of rows actually removed. Robust to
        out-of-range and duplicate indices. Performs a single model
        reset so the proxy and selection caches re-sync cleanly.
        """
        valid = sorted({r for r in rows if 0 <= r < len(self._data)},
                       reverse=True)
        if not valid:
            return 0
        self.beginResetModel()
        for r in valid:
            del self._data[r]
        self._last_validation_error = ""
        self.endResetModel()
        return len(valid)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._columns[section].header_text
            if role == Qt.ItemDataRole.ToolTipRole:
                return self._columns[section].description_text
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        row = self._data[index.row()]
        return self._columns[index.column()].getter(row)

    def setData(
        self,
        index: QModelIndex,
        value: object,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        try:
            self._columns[index.column()].setter(self._data[index.row()], value)
        except (TypeError, ValueError) as exc:
            self._last_validation_error = str(exc)
            self.validation_failed.emit(self._last_validation_error)
            return False
        self._last_validation_error = ""
        self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.isValid():
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags




class DataTableWidget(QWidget):
    """Reusable table shell with title, search, state, and selection summary."""

    rows_deleted = Signal(int)  # Feedback #2 — count of rows just removed.

    def __init__(
        self,
        title: str,
        accessible_name: str,
        columns: list[ColumnDefinition[T]],
        title_key: str = "",
        accessible_name_key: str = "",
    ) -> None:
        super().__init__()
        self._title_text = title
        self._title_key = title_key
        self._accessible_name = accessible_name
        self._accessible_name_key = accessible_name_key
        self._columns = columns
        self.setObjectName("dataTablePanel")
        set_accessibility(
            self,
            self._translated_accessible_name(),
            tr("tables.common.panel_description", title=self._translated_title()),
        )

        self._source_model = EditableTableModel(columns)
        self._source_model.validation_failed.connect(self._on_validation_failed)

        self._proxy_model = TableFilterProxyModel()
        self._proxy_model.setSourceModel(self._source_model)

        # Detect the material column once — its header_key ends with ".material".
        self._material_column = self._detect_material_column(columns)
        if self._material_column is not None:
            self._proxy_model.set_material_column(self._material_column)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._title = QLabel(self._translated_title())
        self._title.setObjectName("dataTableTitle")
        set_accessibility(
            self._title,
            tr("tables.common.heading", title=self._translated_title()),
        )
        header.addWidget(self._title)

        header.addStretch()

        # Feedback v2 #3 — visible delete affordance.
        # Same handler as Delete/Backspace/context-menu; hidden until
        # the user selects at least one row to avoid clutter.
        self._delete_button = QPushButton(tr("tables.common.delete_button"))
        self._delete_button.setObjectName("deleteSelectedButton")
        self._delete_button.setProperty("variant", "destructive-secondary")
        self._delete_button.setToolTip(tr("tables.common.delete_button_tooltip"))
        set_accessibility(
            self._delete_button,
            tr("tables.common.delete_selected"),
            tr("tables.common.delete_button_tooltip"),
        )
        self._delete_button.clicked.connect(self.delete_selected_rows)
        self._delete_button.setVisible(False)
        header.addWidget(self._delete_button)

        self._selection_label = QLabel(tr("tables.common.selected", count=0))
        self._selection_label.setProperty("role", "helper")
        set_accessibility(
            self._selection_label,
            tr("tables.common.selection_count_name", title=self._translated_title()),
        )
        header.addWidget(self._selection_label)
        layout.addLayout(header)

        self._filter_bar = TableFilterBar()
        self._filter_bar.text_changed.connect(self._proxy_model.set_filter_text)
        self._filter_bar.materials_changed.connect(self._proxy_model.set_materials)
        set_accessibility(
            self._filter_bar,
            tr("tables.common.search_placeholder"),
            tr("tables.common.table_description"),
        )
        layout.addWidget(self._filter_bar)

        self._state_label = QLabel(tr("tables.common.no_data"))
        self._state_label.setObjectName("tableState")
        self._state_label.setWordWrap(True)
        self._state_label.setProperty("status", "empty")
        set_accessibility(
            self._state_label,
            f"{self._translated_title()} table state",
            tr("tables.common.no_data"),
        )
        layout.addWidget(self._state_label)

        self._table = QTableView()
        self._table.setObjectName("dataTable")
        self._table.setModel(self._proxy_model)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.selectionModel().selectionChanged.connect(self._update_selection_state)
        if self._material_column is not None:
            self._table.setItemDelegateForColumn(
                self._material_column, MaterialChipDelegate(self._table),
            )
        set_accessibility(
            self._table,
            self._translated_accessible_name(),
            tr("tables.common.table_description"),
        )
        layout.addWidget(self._table)

        # Feedback #2 — per-row delete via keyboard + context menu.
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self.delete_selected_rows)
        backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self._table)
        backspace_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        backspace_shortcut.activated.connect(self.delete_selected_rows)

        self._explicit_state: tuple[str, str] | None = None
        self._update_state()

    @property
    def source_model(self) -> EditableTableModel:
        return self._source_model

    @property
    def table(self) -> QTableView:
        return self._table

    @property
    def state_message(self) -> str:
        return self._state_label.text()

    def set_rows(self, rows: Iterable[T]) -> None:
        import sys
        self._explicit_state = None
        materialized = list(rows)
        self._source_model.set_data(materialized)
        if self._material_column is not None:
            self._refresh_material_chips(materialized)
        self._update_state()
        if sys.stdout is not None:
            proxy_rc = self._proxy_model.rowCount()
            mat_filter = getattr(self._proxy_model, "_materials", "?")
            txt_filter = getattr(self._proxy_model, "_filter_text", "?")
            print(
                f"[TABLE SYS] set_rows  source={self._source_model.rowCount()}"
                f"  proxy={proxy_rc}  mat_filter={mat_filter!r}"
                f"  txt_filter={txt_filter!r}",
                flush=True,
            )

    def add_row(self, row: T) -> None:
        self._explicit_state = None
        self._source_model.add_row(row)
        if self._material_column is not None:
            self._refresh_material_chips(self._source_model.get_data())
        self._update_state()

    def get_rows(self) -> list:
        return self._source_model.get_data()

    def clear(self) -> None:
        self._explicit_state = None
        self._source_model.clear()
        if self._material_column is not None:
            self._filter_bar.set_materials([])
        self._update_state()

    def filter_text(self, text: str) -> None:
        """Programmatic filter (synchronous, bypasses debounce)."""
        # Block signal to avoid firing the debounce timer twice; we
        # apply the filter directly so callers (and tests) see the
        # effect on the next event-loop tick.
        self._filter_bar._search.blockSignals(True)
        self._filter_bar._search.setText(text)
        self._filter_bar._search.blockSignals(False)
        self._proxy_model.set_filter_text(text)

    def set_state(self, message: str, status: str = "ready") -> None:
        self._explicit_state = (message, status)
        self._apply_state(message, status)

    def retranslate(self) -> None:
        self._title.setText(self._translated_title())
        set_accessibility(
            self,
            self._translated_accessible_name(),
            tr("tables.common.panel_description", title=self._translated_title()),
        )
        set_accessibility(
            self._title,
            tr("tables.common.heading", title=self._translated_title()),
        )
        self._filter_bar.retranslate()
        self._delete_button.setText(tr("tables.common.delete_button"))
        self._delete_button.setToolTip(tr("tables.common.delete_button_tooltip"))
        set_accessibility(
            self._delete_button,
            tr("tables.common.delete_selected"),
            tr("tables.common.delete_button_tooltip"),
        )
        set_accessibility(
            self._table,
            self._translated_accessible_name(),
            tr("tables.common.table_description"),
        )
        if self._source_model.columnCount() > 0:
            self._source_model.headerDataChanged.emit(
                Qt.Orientation.Horizontal,
                0,
                self._source_model.columnCount() - 1,
            )
        self._update_state()

    def set_title_text(self, title: str) -> None:
        self._title_text = title
        self.retranslate()

    def selection_count(self) -> int:
        return len(self._table.selectionModel().selectedRows())

    # ── Row deletion (feedback #2) ────────────────────────────

    def delete_selected_rows(self) -> int:
        """Delete the rows currently selected in the view.

        Maps proxy rows back to source rows so sort/filter state does
        not corrupt the removal. Emits ``rows_deleted`` with the count
        so hosts can sync downstream state (presenters, persistence).
        """
        selection = self._table.selectionModel()
        if selection is None:
            return 0
        proxy_rows = selection.selectedRows()
        if not proxy_rows:
            return 0
        source_rows = [
            self._proxy_model.mapToSource(idx).row()
            for idx in proxy_rows
        ]
        removed = self._source_model.remove_rows(source_rows)
        if removed:
            if self._material_column is not None:
                self._refresh_material_chips(self._source_model.get_data())
            self._update_state()
            self._update_selection_state()
            self.rows_deleted.emit(removed)
        return removed

    def _show_context_menu(self, pos) -> None:
        if self.selection_count() == 0:
            return
        menu = QMenu(self._table)
        action = QAction(tr("tables.common.delete_selected"), menu)
        action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        action.triggered.connect(self.delete_selected_rows)
        menu.addAction(action)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _on_validation_failed(self, message: str) -> None:
        self.set_state(tr_error(message), "error")

    def _update_selection_state(self) -> None:
        count = self.selection_count()
        text = tr("tables.common.selected", count=count)
        self._selection_label.setText(text)
        self._selection_label.setAccessibleDescription(text)
        self._delete_button.setVisible(count > 0)
        self._delete_button.setEnabled(count > 0)

    def _update_state(self) -> None:
        if self._explicit_state is not None:
            self._apply_state(*self._explicit_state)
            return
        row_count = self._source_model.rowCount()
        if row_count == 0:
            self._apply_state(tr("tables.common.no_data"), "empty")
        else:
            self._apply_state(tr("tables.common.rows_loaded", count=row_count), "success")
        self._update_selection_state()

    def _apply_state(self, message: str, status: str) -> None:
        self._state_label.setText(message)
        self._state_label.setAccessibleDescription(message)
        set_ui_property(self._state_label, "status", status)
        set_ui_property(self._table, "tableState", status)

    def _translated_title(self) -> str:
        return tr(self._title_key) if self._title_key else self._title_text

    def _translated_accessible_name(self) -> str:
        if self._accessible_name_key:
            return tr(self._accessible_name_key, title=self._translated_title())
        return self._accessible_name

    @staticmethod
    def _detect_material_column(columns: list[ColumnDefinition[T]]) -> int | None:
        """Return the column index whose ``header_key`` ends with ``.material``."""
        for idx, col in enumerate(columns):
            if col.header_key.endswith(".material"):
                return idx
        return None

    def _refresh_material_chips(self, rows: Iterable[T]) -> None:
        """Rebuild the material chip row from distinct values in the column."""
        if self._material_column is None:
            return
        getter = self._columns[self._material_column].getter
        seen: list[str] = []
        for row in rows:
            value = str(getter(row) or "").strip().upper()
            if value and value not in seen:
                seen.append(value)
        self._filter_bar.set_materials(sorted(seen))


def positive_int(value: object, label: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return parsed


def positive_float(value: object, label: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return parsed


def integer_value(value: object, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer.") from exc


def text_value(value: object) -> str:
    return str(value).strip()

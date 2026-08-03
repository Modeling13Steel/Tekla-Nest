"""Sort/filter proxy model used by ``DataTableWidget``.

Separated from ``table_system.py`` to keep that file under the
ROADMAP §10.3 LOC budget. The proxy supports two AND-combined
filters:

* Full-text search across every visible column (case-insensitive).
* A material chip filter, scoped to a single configured column index.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt


class TableFilterProxyModel(QSortFilterProxyModel):
    """Case-insensitive row filter across all visible columns.

    Supports an optional material chip filter — when ``set_materials`` is
    given a non-empty set, only rows whose ``material_column`` value is
    in the set survive. The two filters AND together (search text *and*
    material chip).
    """

    def __init__(self) -> None:
        super().__init__()
        self._filter_text = ""
        self._materials: set[str] = set()
        self._material_column: int | None = None
        self.setDynamicSortFilter(True)

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self.beginFilterChange()
        self.endFilterChange()

    def set_material_column(self, column: int | None) -> None:
        self._material_column = column
        self.beginFilterChange()
        self.endFilterChange()

    def set_materials(self, materials: set[str]) -> None:
        self._materials = {m.strip().upper() for m in materials if m and m.strip()}
        self.beginFilterChange()
        self.endFilterChange()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        if self._materials and self._material_column is not None:
            index = model.index(source_row, self._material_column, source_parent)
            value = str(model.data(index, Qt.ItemDataRole.DisplayRole) or "").strip().upper()
            if value not in self._materials:
                return False
        if not self._filter_text:
            return True
        for column in range(model.columnCount(source_parent)):
            index = model.index(source_row, column, source_parent)
            value = model.data(index, Qt.ItemDataRole.DisplayRole)
            if self._filter_text in str(value).lower():
                return True
        return False

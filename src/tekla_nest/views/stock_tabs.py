"""Stock tabs widget (Market + Client).

Replaces: C# tabControlStock with dataGridView2 (Market) + dataGridView3 (Client)
"""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QTabWidget

from ..config.app_config import get_config
from ..design_system import set_accessibility
from ..i18n import tr
from ..models import StockEntry
from .stock_table import StockTableWidget


class StockTabsWidget(QTabWidget):
    """Two-tab widget separating Market and Client stock entries."""

    def __init__(self) -> None:
        super().__init__()
        set_accessibility(self, tr("tables.stock.tabs_name"), tr("tables.stock.tabs_description"))
        self._market = StockTableWidget(tr("tables.stock.market_title"), include_priority=False)
        self._client = StockTableWidget(tr("tables.stock.client_title"))
        self.addTab(self._market, tr("tables.stock.market_tab"))
        self.addTab(self._client, tr("tables.stock.client_tab"))
        # Market tab only: the trim applies to factory bars, not client offcuts.
        self._end_trim = QCheckBox(self._market)
        self._end_trim.setObjectName("endTrimCheck")
        self._end_trim.setContentsMargins(8, 6, 8, 0)
        self._market.layout().insertWidget(0, self._end_trim)
        self._retranslate_trim()

    def end_trim_enabled(self) -> bool:
        return self._end_trim.isChecked()

    def _retranslate_trim(self) -> None:
        mm = f"{get_config().end_trim:g}"
        self._end_trim.setText(tr("tables.stock.end_trim", mm=mm))
        self._end_trim.setToolTip(tr("tables.stock.end_trim_tip", mm=mm))

    def add_stock(self, entries: list[StockEntry]) -> None:
        """Route each entry to the correct tab based on source."""
        for e in entries:
            if e.source == "Cliente":
                self._client.add_entry(e)
            else:
                self._market.add_entry(e)

    def set_market_stock(self, entries: list[StockEntry]) -> None:
        self._market.set_entries(entries)

    def set_client_stock(self, entries: list[StockEntry]) -> None:
        self._client.set_entries(entries)

    def get_market_stock(self) -> list[StockEntry]:
        return self._market.get_entries()

    def get_client_stock(self) -> list[StockEntry]:
        return self._client.get_entries()

    def clear_market(self) -> None:
        self._market.clear()

    def clear_client(self) -> None:
        self._client.clear()

    def retranslate(self) -> None:
        set_accessibility(self, tr("tables.stock.tabs_name"), tr("tables.stock.tabs_description"))
        self.setTabText(0, tr("tables.stock.market_tab"))
        self.setTabText(1, tr("tables.stock.client_tab"))
        self._market.retranslate(tr("tables.stock.market_title"))
        self._client.retranslate(tr("tables.stock.client_title"))
        self._retranslate_trim()

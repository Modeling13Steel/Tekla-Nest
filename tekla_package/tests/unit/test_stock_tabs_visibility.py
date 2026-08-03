"""Feedback #3 + #4 — Market Stock tab visibility checks.

#3 — Market Stock must NOT show the Reference (priority) column. That
    column is meaningful only for Client stock.
#4 — Market Stock auto-populated from `generate_default_stock` must
    surface one row per (profile, length, material) so the user can see
    the material breakdown.
"""

from __future__ import annotations

import pytest
from tekla_common.config.app_config import get_config, load_config, reset_config
from tekla_common.i18n import set_language, tr
from tekla_nest.services.stock_rules import generate_default_stock
from tekla_nest.views.stock_tabs import StockTabsWidget


@pytest.fixture(autouse=True)
def _cfg():
    reset_config()
    load_config("/tmp/nonexistent_config_stock_tabs.yaml")
    set_language("en")
    yield
    set_language("en")
    reset_config()


# ── #3 — no Reference column on Market ───────────────────────────


def test_market_stock_table_has_no_reference_column(qtbot):
    widget = StockTabsWidget()
    qtbot.addWidget(widget)

    market = widget._market
    headers = [
        market._table.model().headerData(c, market._table.horizontalHeader().orientation())
        for c in range(market._table.model().columnCount())
    ]
    reference_label = tr("tables.stock.headers.priority")
    assert reference_label == "Reference"
    assert reference_label not in headers, (
        f"Market Stock should not show 'Reference' column. Headers: {headers}"
    )


def test_client_stock_table_still_has_reference_column(qtbot):
    widget = StockTabsWidget()
    qtbot.addWidget(widget)

    client = widget._client
    headers = [
        client._table.model().headerData(c, client._table.horizontalHeader().orientation())
        for c in range(client._table.model().columnCount())
    ]
    reference_label = tr("tables.stock.headers.priority")
    assert reference_label in headers


# ── #4 — material per class in Market Stock ──────────────────────


def test_auto_market_stock_emits_one_row_per_material():
    """generate_default_stock produces one StockEntry per (profile, material) pair
    passed in. Callers supply explicit pairs; this test exercises three materials."""
    cfg = get_config()
    pairs = [("HEA240", m) for m in cfg.materials]
    stock = generate_default_stock(pairs)

    # For each length × material combo there must be exactly one entry.
    materials_seen = {s.material for s in stock if s.profile == "HEA240"}
    assert materials_seen == set(cfg.materials), (
        f"expected materials={set(cfg.materials)}, got {materials_seen}"
    )

    # And every length should appear with EVERY material.
    lengths = {s.length for s in stock if s.profile == "HEA240"}
    for length in lengths:
        mats_for_length = {
            s.material for s in stock if s.profile == "HEA240" and s.length == length
        }
        assert mats_for_length == set(cfg.materials), (
            f"length {length} mm missing materials: {set(cfg.materials) - mats_for_length}"
        )


def test_market_stock_tab_renders_material_rows(qtbot):
    """When auto-populated stock is loaded into the Market tab, the
    Material column shows distinct values."""
    widget = StockTabsWidget()
    qtbot.addWidget(widget)

    cfg = get_config()
    pairs = [("HEA240", m) for m in cfg.materials]
    stock = generate_default_stock(pairs)
    widget.set_market_stock(stock)

    market = widget._market
    model = market._table.model()

    # Find the Material column index.
    headers = [
        model.headerData(c, market._table.horizontalHeader().orientation())
        for c in range(model.columnCount())
    ]
    material_label = tr("tables.stock.headers.material")
    assert material_label in headers, f"no Material column among {headers}"
    material_col = headers.index(material_label)

    materials_in_view = {model.data(model.index(r, material_col)) for r in range(model.rowCount())}
    materials_in_view.discard(None)
    materials_in_view.discard("")
    assert len(materials_in_view) >= 2, (
        f"Market Stock view collapses materials: only {materials_in_view}"
    )

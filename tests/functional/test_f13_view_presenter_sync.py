"""F13 — view → presenter sync before optimize / auto-stock.

The parts table and stock tabs are user-editable in place. Without an
explicit sync, the presenter would optimize against a stale list — the
symptom being "no stock available for this profile" on the report,
because the presenter saw zero profiles when auto-stock was clicked.

These tests pin the sync behavior so the regression cannot return.
"""
from __future__ import annotations

from tekla_nest.models import PartEntry, StockEntry


def test_auto_stock_seeds_from_parts_edited_in_table(window, presenter):
    """User adds parts manually in the table → auto-stock seeds them.

    Regression: previously the presenter's ``_parts`` list lagged
    behind the table because edits/additions were not pushed back.
    Clicking Auto-stock then seeded from an empty profile list and
    the resulting Optimize/Report path produced "no stock available".
    """
    # Simulate the user typing 2 rows into the parts table directly
    # (no CSV, no provider) — presenter starts empty.
    assert presenter._parts == []
    window._parts_table.set_parts([
        PartEntry(quantity=2, length=3000, reference="P1",
                  profile="IPE200", material="S275JR"),
        PartEntry(quantity=1, length=4500, reference="P2",
                  profile="IPE200", material="S275JR"),
    ])

    # Click "Auto-stock" via the window-level slot the menu now uses
    window._on_auto_stock()

    # Presenter must now have the parts AND non-empty market stock
    assert len(presenter._parts) == 2
    assert len(presenter._market_stock) > 0
    assert any(s.profile == "IPE200" for s in presenter._market_stock)


def test_calculate_optimizes_against_table_contents(window, presenter, qtbot):
    """User adds parts + clicks Calculate → optimization sees the parts."""
    window._parts_table.set_parts([
        PartEntry(quantity=2, length=3000, reference="P1",
                  profile="IPE200", material="S275JR"),
    ])
    window._on_auto_stock()

    # Drive the synchronous engine via the same sync helper to avoid
    # the async thread plumbing in this unit-style test.
    window._sync_view_to_presenter()
    presenter.run_optimization()

    result = presenter._last_result
    assert result is not None
    assert len(result.profiles) == 1
    p = result.profiles[0]
    assert p.profile == "IPE200"
    # Critically: there IS stock, so we got bars — not "no stock"
    assert len(p.bars) >= 1


def test_calculate_picks_up_stock_edited_in_table(window, presenter):
    """Manual stock entries in the stock tabs are sent to the presenter."""
    window._parts_table.set_parts([
        PartEntry(quantity=1, length=3000, reference="P1",
                  profile="IPE200", material="S275JR"),
    ])
    # User manually populates a single client bar in the stock tab
    window._stock_tabs.set_client_stock([
        StockEntry(quantity=1, length=6000, priority=1,
                   profile="IPE200", material="S275JR", source="Cliente"),
    ])

    window._sync_view_to_presenter()

    assert any(
        s.profile == "IPE200" and s.source == "Cliente"
        for s in presenter._client_stock
    )
    presenter.run_optimization()
    result = presenter._last_result
    assert result is not None and len(result.profiles) == 1
    # Engine must have used the client bar
    p = result.profiles[0]
    assert len(p.bars) >= 1
    assert any(bar.source == "Cliente" for bar in p.bars)

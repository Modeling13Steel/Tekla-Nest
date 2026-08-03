"""F2 — Stock loading (Feedback #3, #4, #5, #11)."""

from __future__ import annotations


class TestAutoPopulateStock:
    def test_auto_stock_after_parts_creates_entries(
        self,
        journey,
        parts_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        assert journey.presenter.has_stock
        assert collector.errors == []

    def test_auto_stock_without_parts_is_noop(
        self,
        journey,
        collector,
    ):
        journey.auto_stock()
        # Auto-stock with no parts should not throw, but should not
        # silently pretend it has done useful work either.
        assert collector.errors == []
        # Stock should remain empty when there are no parts.
        assert not journey.presenter.has_stock


class TestClientStock:
    def test_client_csv_is_routed_to_client_stock(
        self,
        journey,
        parts_csv_factory,
        stock_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        journey.load_client_stock(stock_csv_factory())
        assert journey.presenter.has_stock
        # Client stock should be loaded
        assert len(journey.presenter._client_stock) > 0

    def test_client_loaded_after_market_keeps_both(
        self,
        journey,
        parts_csv_factory,
        stock_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        market_len = len(journey.presenter._market_stock)
        assert market_len > 0

        journey.load_client_stock(stock_csv_factory())
        assert len(journey.presenter._market_stock) == market_len
        assert len(journey.presenter._client_stock) > 0


class TestMarketTabHasNoReferenceColumn:
    """Pin Feedback #3 — Market tab excludes the priority/reference column.

    In the legacy C# UI the priority column was labelled "Referencia".
    Feedback #3 asks that the Market tab not show this column at all.
    """

    def test_market_table_columns_exclude_priority(self, journey):
        market_table = journey.window._stock_tabs._market
        headers = [c.header_key for c in market_table._table_widget._columns]
        assert not any(h.endswith(".priority") for h in headers), (
            f"Feedback #3 regression — priority/reference column in Market tab: {headers}"
        )

    def test_client_table_keeps_priority(self, journey):
        client_table = journey.window._stock_tabs._client
        headers = [c.header_key for c in client_table._table_widget._columns]
        assert any(h.endswith(".priority") for h in headers), (
            "Client tab must keep the priority column"
        )

    def test_both_tables_keep_material(self, journey):
        """Pin Feedback #4 — material visible in both tabs."""
        for table_attr in ("_market", "_client"):
            table = getattr(journey.window._stock_tabs, table_attr)
            headers = [c.header_key for c in table._table_widget._columns]
            assert any(h.endswith(".material") for h in headers), (
                f"Feedback #4 regression — material missing from {table_attr}"
            )


class TestClientStockConsumedFirst:
    """Pin Feedback #11 — client stock (priority<0) is consumed first."""

    def test_client_priority_wins(self, journey, parts_csv_factory, tmp_path):
        # Load parts that need exactly one bar of HEA240
        csv = parts_csv_factory(
            rows=[
                [1, 5500, "X1", "HEA240", "S275JR"],
            ],
            name="single.csv",
        )
        journey.load_parts(csv)

        # Client has a 6000 bar; market has a 6000 bar — client should win
        stock = tmp_path / "stock.csv"
        with open(stock, "w", encoding="utf-8") as f:
            f.write("Quantidade;comprimento;prioridade;perfil;material\n")
            f.write("1;6000;-1;HEA240;S275JR\n")  # client
        journey.load_client_stock(stock)
        # Also auto-populate market stock
        journey.auto_stock()

        journey.calculate()
        result = journey.presenter._last_result
        assert result and result.profiles
        # All bars used should be Cliente (priority<0), not Mercado
        bars = result.profiles[0].bars
        assert bars, "No bars in result"
        for bar in bars:
            assert bar.source == "Cliente", (
                f"Feedback #11 regression — market bar used while client was available: {bar}"
            )

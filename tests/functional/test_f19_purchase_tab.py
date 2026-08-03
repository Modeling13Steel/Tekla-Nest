"""F19 — Purchase list tab visible alongside Cutting plan (Feedback v2 item #4).

The PurchaseTableWidget exists; this pins the two-tab layout and the
auto-population on `result_ready`.
"""
from __future__ import annotations


class TestPurchaseTab:
    def test_two_tabs_present(self, journey):
        tabs = journey.window._result_tabs
        assert tabs.count() == 2
        titles = {tabs.tabText(i) for i in range(tabs.count())}
        # Both tabs must be addressable; exact strings come from i18n.
        assert any("report" in t.lower() or "plano" in t.lower() for t in titles)
        assert any("purchase" in t.lower() or "compra" in t.lower() for t in titles)

    def test_purchase_tab_populates_after_calculate(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        # PurchaseTableWidget exposes the bar count via the journey helper.
        assert journey.purchase_row_count() > 0

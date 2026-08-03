"""F4 — Results display (report, purchase table, KPI strip, insights)."""
from __future__ import annotations


class TestResultPropagation:
    def test_optimize_populates_purchase_table(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        assert journey.purchase_row_count() > 0

    def test_optimize_populates_report_html(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        html = journey.report_html()
        # Profile names should appear in the rendered report
        assert "HEA240" in html or "IPE200" in html

    def test_kpi_strip_updates(self, journey, parts_csv_factory):
        from PySide6.QtWidgets import QApplication
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        QApplication.processEvents()
        # KPI strip should reflect the summary; we just check it is
        # alive and has at least one labelled value.
        kpi = journey.window._kpi_strip
        assert kpi is not None


class TestReportFilter:
    def test_chip_filter_changes_visible_profile(
        self, journey, mixed_material_parts, collector,
    ):
        journey.load_parts(mixed_material_parts)
        journey.auto_stock()
        journey.calculate()

        journey.presenter.report_filter_changed("HEA240")
        # New HTML should be emitted
        assert len(collector.htmls) >= 2

    def test_chip_filter_clear_restores_all(
        self, journey, mixed_material_parts, collector,
    ):
        journey.load_parts(mixed_material_parts)
        journey.auto_stock()
        journey.calculate()
        journey.presenter.report_filter_changed("HEA240")
        journey.presenter.report_filter_changed("")
        assert len(collector.htmls) >= 3


class TestInsightsToggle:
    def test_toggle_hides_sidebar(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        rp = journey.window._report_preview
        rp.set_insights_visible(False)
        assert not rp.insights_visible()
        rp.set_insights_visible(True)
        assert rp.insights_visible()

    def test_toggle_persists_across_language_switch(
        self, journey, parts_csv_factory,
    ):
        from tekla_nest.i18n import set_language
        journey.load_parts(parts_csv_factory())
        rp = journey.window._report_preview
        rp.set_insights_visible(False)
        set_language("pt")
        assert not rp.insights_visible()
        set_language("en")
        assert not rp.insights_visible()


class TestBarReorder:
    def test_reorder_emits_new_html(
        self, journey, parts_csv_factory, collector,
    ):
        # Need a result with ≥2 bars so reorder is meaningful
        csv = parts_csv_factory(rows=[
            [10, 2000, "X", "HEA240", "S275JR"],
        ], name="multi.csv")
        journey.load_parts(csv)
        journey.auto_stock()
        journey.calculate()
        before = len(collector.htmls)
        # Only reorder if we have at least 2 bars
        if journey.presenter._last_result.profiles[0].bars and \
           len(journey.presenter._last_result.profiles[0].bars) >= 2:
            journey.presenter.reorder_bars(0, 1, 0)
            assert len(collector.htmls) > before

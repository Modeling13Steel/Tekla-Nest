"""F16 — Operator-prep header in cutting plan (Feedback v2 item #2).

Per profile, the report shows a "bar prep" line listing each distinct
bar length used + the count, plus a totals row. Driven by the shared
``aggregate_prep`` so it never drifts from the Excel / CSV / in-app
purchase aggregation.
"""

from __future__ import annotations


class TestPrepHeader:
    def test_html_contains_prep_block(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        from tekla_nest.services.pdf_report import render_report_html

        html = render_report_html(journey.presenter._last_result)
        assert 'class="prep-header"' in html
        # At least one prep chip rendered (a "Bar … × …" entry).
        assert "prep-chip" in html
        # Total line present (i18n: "Total:" in EN/PT).
        assert "prep-total" in html

    def test_prep_totals_match_aggregation(self, journey, parts_csv_factory):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        from tekla_nest.services.bar_aggregation import aggregate_prep

        prep = aggregate_prep(journey.presenter._last_result)
        assert prep, "no profiles in result"
        # Bar count must equal sum of by_length counts (no drift).
        for p in prep:
            assert p.total_bars == sum(c for _, c in p.by_length)
            expected_m = sum(ln * c for ln, c in p.by_length) / 1000.0
            assert abs(p.linear_m - expected_m) < 1e-6

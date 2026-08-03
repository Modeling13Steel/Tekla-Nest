"""Verify M5 HTML template renders unfit pieces with amber card + KPI hero."""
from __future__ import annotations

from tekla_nest.models import BarResult, CutPiece, NestResult, ProfileResult
from tekla_nest.services.pdf_report import render_report_html


def _profile_with_unfit() -> ProfileResult:
    return ProfileResult(
        profile="HEA240",
        bars=[BarResult(original_length=6000.0, mark="B1", material="S275JR", source="Mercado", cuts=[2000.0])],
        waste_pct=15.0,
        unfit_pieces=[CutPiece(length=7000.0, mark="BIG"), CutPiece(length=5500.0, mark="MED")],
    )


def test_html_contains_kpi_hero_and_unfit_card() -> None:
    html = render_report_html(NestResult(profiles=[_profile_with_unfit()]))
    assert "kpi-hero" in html
    assert "kpi-card" in html
    # Amber unfit card markup (not just CSS) + unfit pieces listed
    assert 'class="unfit-card"' in html
    assert "BIG" in html
    assert "7000" in html
    # Cut-bar SVG viz present
    assert "<svg" in html
    assert 'viewBox="0 0 600 14"' in html
    # KPI warning class applied when unfit > 0
    assert "kpi-card kpi-warning" in html


def test_html_unfit_card_absent_when_all_pieces_fit() -> None:
    profile = ProfileResult(
        profile="IPE100",
        bars=[BarResult(original_length=6000.0, mark="B1", material="S275JR", source="Mercado", cuts=[1000.0])],
        waste_pct=8.0,
    )
    html = render_report_html(NestResult(profiles=[profile]))
    assert 'class="unfit-card"' not in html
    assert "kpi-card kpi-warning" not in html

"""Tests for the insights heuristics engine."""

from __future__ import annotations

from tekla_nest.models import (
    BarResult,
    CutPiece,
    NestResult,
    ProfileResult,
)
from tekla_nest.services.insights import (
    HIGH_WASTE_THRESHOLD_PCT,
    Insight,
    suggest,
)


def _bar(material: str = "S275JR", length: float = 6000.0, used: float = 0.0) -> BarResult:
    return BarResult(
        original_length=length,
        mark="B1",
        material=material,
        source="Mercado",
        cuts=[used] if used else [],
    )


def _piece(length: float, mark: str = "PX") -> CutPiece:
    return CutPiece(length=length, mark=mark)


def test_no_result_returns_empty() -> None:
    assert suggest(None) == []
    assert suggest(NestResult()) == []


def test_add_stock_when_unfit_present() -> None:
    profile = ProfileResult(
        profile="HEA240",
        bars=[_bar()],
        unfit_pieces=[_piece(7000.0, "BIG"), _piece(5500.0, "MED")],
    )
    insights = suggest(NestResult(profiles=[profile]))
    add_stock = [i for i in insights if i.insight_id.startswith("add_stock:")]
    assert len(add_stock) == 1
    assert add_stock[0].action == "request_stock"
    ctx = add_stock[0].context_dict()
    assert ctx["profile"] == "HEA240"
    assert ctx["length"] == 7000.0  # longest unfit piece
    assert ctx["piece_count"] == 2


def test_high_waste_above_threshold() -> None:
    profile = ProfileResult(
        profile="IPE200",
        bars=[_bar()],
        waste_pct=HIGH_WASTE_THRESHOLD_PCT + 5,
    )
    insights = suggest(NestResult(profiles=[profile]))
    matches = [i for i in insights if i.insight_id == "high_waste:IPE200"]
    assert len(matches) == 1
    assert matches[0].severity == "warning"


def test_high_waste_at_threshold_not_flagged() -> None:
    profile = ProfileResult(
        profile="IPE200",
        bars=[_bar()],
        waste_pct=HIGH_WASTE_THRESHOLD_PCT,
    )
    insights = suggest(NestResult(profiles=[profile]))
    assert not any(i.insight_id.startswith("high_waste:") for i in insights)


def test_mixed_materials_detected() -> None:
    profile = ProfileResult(
        profile="HEA240",
        bars=[_bar(material="S275JR"), _bar(material="S355JR")],
    )
    insights = suggest(NestResult(profiles=[profile]))
    matches = [i for i in insights if i.insight_id.startswith("mixed_materials:")]
    assert len(matches) == 1
    ctx = matches[0].context_dict()
    assert ctx["material_count"] == 2


def test_single_material_not_flagged() -> None:
    profile = ProfileResult(
        profile="HEA240",
        bars=[_bar(material="S275JR"), _bar(material="S275JR")],
    )
    insights = suggest(NestResult(profiles=[profile]))
    assert not any(i.insight_id.startswith("mixed_materials:") for i in insights)


def test_ordering_add_stock_before_high_waste() -> None:
    profile = ProfileResult(
        profile="HEA240",
        bars=[_bar()],
        waste_pct=40.0,
        unfit_pieces=[_piece(7000.0)],
    )
    ids = [i.insight_id for i in suggest(NestResult(profiles=[profile]))]
    assert ids.index("add_stock:HEA240") < ids.index("high_waste:HEA240")


def test_insight_is_frozen_dataclass() -> None:
    import pytest

    i = Insight(
        insight_id="x",
        severity="info",
        title_key="k",
        detail_key="d",
    )
    with pytest.raises(Exception):
        i.severity = "danger"  # type: ignore[misc]

"""Tests for OptimizationSummary view-model."""
from __future__ import annotations

import pytest

from tekla_nest.models import (
    BarResult,
    CutPiece,
    NestResult,
    OptimizationSummary,
    ProfileResult,
)


def _bar(length: float = 6000.0, used: float = 0.0) -> BarResult:
    return BarResult(
        original_length=length,
        mark="B1",
        material="S275JR",
        source="Mercado",
        cuts=[used] if used else [],
    )


def _piece(length: float = 500.0) -> CutPiece:
    return CutPiece(length=length, mark="M1")


class TestOptimizationSummaryFromNestResult:
    def test_none_in_returns_none(self) -> None:
        assert OptimizationSummary.from_nest_result(None) is None

    def test_empty_result_returns_none(self) -> None:
        assert OptimizationSummary.from_nest_result(NestResult()) is None

    def test_full_fit_no_unfit(self) -> None:
        # bar 6000, 5400 used → 600 waste = 10% (overall_waste_pct computed on result)
        bar = _bar(6000.0, used=5400.0)
        result = NestResult(
            profiles=[ProfileResult(profile="HEA240", bars=[bar], waste_pct=10.0)]
        )
        s = OptimizationSummary.from_nest_result(result)
        assert s is not None
        assert s.bars_used == 1
        assert s.unfit_count == 0
        assert s.profile_count == 1
        assert s.waste_pct == pytest.approx(10.0)
        assert s.has_unfit is False

    def test_unfit_pieces_counted(self) -> None:
        pr = ProfileResult(
            profile="HEA240",
            bars=[_bar(), _bar()],
            unfit_pieces=[_piece(), _piece(), _piece()],
        )
        result = NestResult(profiles=[pr])
        s = OptimizationSummary.from_nest_result(result)
        assert s is not None
        assert s.bars_used == 2
        assert s.unfit_count == 3
        assert s.has_unfit is True

    def test_multiple_profiles_aggregated(self) -> None:
        result = NestResult(
            profiles=[
                ProfileResult(profile="HEA240", bars=[_bar(), _bar()]),
                ProfileResult(profile="IPE200", bars=[_bar()], unfit_pieces=[_piece()]),
            ]
        )
        s = OptimizationSummary.from_nest_result(result)
        assert s is not None
        assert s.profile_count == 2
        assert s.bars_used == 3
        assert s.unfit_count == 1

    def test_frozen_dataclass(self) -> None:
        s = OptimizationSummary(waste_pct=1.0, bars_used=1, unfit_count=0, profile_count=1)
        with pytest.raises(Exception):
            s.waste_pct = 5.0  # type: ignore[misc]

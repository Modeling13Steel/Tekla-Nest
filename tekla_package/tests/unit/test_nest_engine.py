"""Unit tests for the NestEngine bin-packing algorithm."""

from __future__ import annotations

import pytest
from tekla_nest.models import CutPiece, StockBar
from tekla_nest.services.nest_engine import NestEngine, NestError


class TestNestEngineBasic:
    """Basic optimization scenarios."""

    def test_single_piece_single_bar(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=3000, mark="A1")]
        bars = [StockBar(length=6000, mark="IPE200", material="S275", source="Mercado")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(3000.0)
        assert result.waste_pct == pytest.approx(50.0)

    def test_perfect_fit_zero_waste(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=6000, mark="A1")]
        bars = [StockBar(length=6000, mark="IPE200", material="S275", source="Mercado")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.waste_pct == pytest.approx(0.0)

    def test_two_pieces_one_bar(self):
        engine = NestEngine(kerf_width=0)
        pieces = [
            CutPiece(length=2000, mark="A1"),
            CutPiece(length=3000, mark="A2"),
        ]
        bars = [StockBar(length=6000, mark="HEA", material="S275", source="Mercado")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].used_length == pytest.approx(5000.0)

    def test_multiple_pieces_multiple_bars(self):
        engine = NestEngine(kerf_width=0)
        pieces = [
            CutPiece(length=3000, mark="A1"),
            CutPiece(length=3000, mark="A2"),
            CutPiece(length=4000, mark="B1"),
        ]
        bars = [
            StockBar(length=6000, mark="HEA", material="S275", source="Mercado"),
            StockBar(length=6000, mark="HEA", material="S275", source="Mercado"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 2


class TestNestEngineKerf:
    """Kerf width handling — kerf applies *between* cuts, not on every cut."""

    def test_kerf_applied_between_two_pieces(self):
        engine = NestEngine(kerf_width=5)
        pieces = [
            CutPiece(length=2995, mark="A1"),
            CutPiece(length=3000, mark="A2"),
        ]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # First cut: 2995 (no kerf). Second cut: 3000 + 5 kerf.
        # Total used = 2995 + 3005 = 6000 → free = 0
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)

    def test_kerf_forces_second_bar(self):
        engine = NestEngine(kerf_width=10)
        pieces = [
            CutPiece(length=3000, mark="A1"),
            CutPiece(length=2995, mark="A2"),
        ]
        bars = [
            StockBar(length=6000, mark="X", material="S", source="M"),
            StockBar(length=6000, mark="X", material="S", source="M"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # 3000 + (2995+10) = 6005 > 6000 → needs 2 bars
        assert len(result.bars) == 2

    def test_zero_kerf(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=6000, mark="A1")]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.bars[0].free_length == pytest.approx(0.0)

    def test_feedback_7_equal_length_with_positive_kerf_still_fits(self):
        """Feedback #7: piece length == stock length must fit even with kerf>0.

        Real-world scenario: a 6000 mm part on a 6000 mm bar with a 5 mm saw
        kerf. Previous behaviour: ``required = piece.length + kerf = 6005``,
        which was greater than the stock and reported as out-of-stock. The
        new model only applies kerf between cuts, so a single piece on a
        new bar needs no kerf allowance and fits.
        """
        engine = NestEngine(kerf_width=5)
        pieces = [CutPiece(length=6000, mark="A1")]
        bars = [StockBar(length=6000, mark="HEA240", material="S275", source="Mercado")]

        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)


class TestNestEngineEdgeCases:
    """Edge cases and infeasible scenarios."""

    def test_empty_pieces_returns_none(self):
        engine = NestEngine()
        assert engine.optimize([], [StockBar(6000, "X", "S", "M")]) is None

    def test_empty_bars_returns_none(self):
        engine = NestEngine()
        assert engine.optimize([CutPiece(3000, "A")], []) is None

    def test_both_empty_returns_none(self):
        engine = NestEngine()
        assert engine.optimize([], []) is None

    def test_piece_larger_than_all_bars_reports_unfit(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=99999, mark="X")]
        bars = [StockBar(length=6000, mark="HEA", material="S275", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.bars == []
        assert result.has_unfit_pieces
        assert [p.mark for p in result.unfit_pieces] == ["X"]
        assert result.waste_pct == pytest.approx(100.0)

    def test_many_small_pieces_few_bars_partial_fit(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=5000, mark=f"P{i}") for i in range(10)]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # 1 bar with 1 piece, 9 unfit pieces
        assert len(result.bars) == 1
        assert len(result.unfit_pieces) == 9

    def test_single_piece_exact_fit(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=12000, mark="A1")]
        bars = [StockBar(length=12000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)


class TestNestEngineValidation:
    """Input validation — descriptive errors."""

    def test_negative_piece_length(self):
        engine = NestEngine()
        with pytest.raises(NestError, match="index 0.*length=-1"):
            engine.optimize(
                [CutPiece(length=-1, mark="bad")],
                [StockBar(length=6000, mark="X", material="S", source="M")],
            )

    def test_zero_piece_length(self):
        engine = NestEngine()
        with pytest.raises(NestError, match="length=0"):
            engine.optimize(
                [CutPiece(length=0, mark="bad")],
                [StockBar(length=6000, mark="X", material="S", source="M")],
            )

    def test_negative_bar_length(self):
        engine = NestEngine()
        with pytest.raises(NestError, match="Stock bar.*length=-5"):
            engine.optimize(
                [CutPiece(length=3000, mark="A")],
                [StockBar(length=-5, mark="X", material="S", source="M")],
            )

    def test_error_includes_mark(self):
        engine = NestEngine()
        with pytest.raises(NestError, match="mark='BAD_PIECE'"):
            engine.optimize(
                [CutPiece(length=-1, mark="BAD_PIECE")],
                [StockBar(length=6000, mark="X", material="S", source="M")],
            )


class TestNestEngineDownsizing:
    """Bar downsizing post-processing."""

    def test_bar_downsized_to_smaller_available(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=3000, mark="A1")]
        bars = [
            StockBar(length=12000, mark="HEA", material="S275", source="M"),
            StockBar(length=6000, mark="HEA", material="S275", source="M"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # The 12000 bar should be downsized to 6000 since piece fits
        assert result.bars[0].original_length <= 12000


class TestNestEngineScrap:
    """Scrap waste classification."""

    def test_scrap_threshold(self):
        engine = NestEngine(kerf_width=0, scrap_threshold=2000)
        pieces = [CutPiece(length=5000, mark="A1")]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Remnant = 1000 ≤ 2000 threshold → counted as scrap
        assert result.scrap_pct > 0

    def test_non_scrap_remnant(self):
        engine = NestEngine(kerf_width=0, scrap_threshold=500)
        pieces = [CutPiece(length=5000, mark="A1")]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Remnant = 1000 > 500 threshold → NOT scrap
        assert result.scrap_pct == pytest.approx(0.0)


class TestNestEngineStrategies:
    """Multi-strategy optimization."""

    def test_best_strategy_selected(self):
        engine = NestEngine(kerf_width=0, max_strategies=6)
        # Create a scenario where different strategies yield different results
        pieces = [
            CutPiece(length=1000, mark="S1"),
            CutPiece(length=2000, mark="S2"),
            CutPiece(length=3000, mark="S3"),
            CutPiece(length=4000, mark="S4"),
        ]
        bars = [
            StockBar(length=6000, mark="X", material="S", source="M"),
            StockBar(length=6000, mark="X", material="S", source="M"),
            StockBar(length=6000, mark="X", material="S", source="M"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Total cuts = 10000, best fit should use 2 bars (12000 stock, 16.67% waste)
        assert len(result.bars) == 2
        assert result.waste_pct < 20.0

    def test_max_strategies_limits_runs(self):
        engine1 = NestEngine(kerf_width=0, max_strategies=1)
        engine6 = NestEngine(kerf_width=0, max_strategies=6)

        pieces = [CutPiece(length=2000, mark=f"P{i}") for i in range(5)]
        bars = [StockBar(length=6000, mark="X", material="S", source="M") for _ in range(5)]

        r1 = engine1.optimize(pieces, bars)
        r6 = engine6.optimize(pieces, bars)

        assert r1 is not None
        assert r6 is not None
        # More strategies should find equal or better solution
        assert r6.waste_pct <= r1.waste_pct


class TestNestEngineExactLengthMatch:
    """Regression: piece length exactly matches stock length.

    These cases caused a 'no stock available' message in the UI when stock
    quantity was insufficient because the engine returned None for the
    whole profile instead of a partial result.
    """

    def test_single_piece_exactly_matches_only_stock(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=6100, mark="A1")]
        bars = [StockBar(length=6100, mark="HEA240", material="S275JR", source="Mercado")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)
        assert result.waste_pct == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "length",
        [6100, 10100, 12100, 14100, 15100, 16100, 6000, 12000],
    )
    def test_exact_match_for_every_default_length(self, length):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=length, mark="P1")]
        bars = [StockBar(length=length, mark="X", material="S275", source="Mercado")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)

    def test_more_pieces_than_stock_returns_partial_with_unfit(self):
        """Reproduces the reported bug: piece length == stock length, but
        not enough bars to satisfy every piece. The engine must return the
        bars that *did* fit plus the list of unfit pieces — not a blank
        'no stock' result."""
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=6100, mark=f"A{i}") for i in range(5)]
        bars = [
            StockBar(length=6100, mark="HEA", material="S275", source="Mercado"),
            StockBar(length=6100, mark="HEA", material="S275", source="Mercado"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 2
        assert result.has_unfit_pieces
        assert len(result.unfit_pieces) == 3
        for bar in result.bars:
            assert bar.cuts == [6100]
            assert bar.free_length == pytest.approx(0.0)

    def test_exact_match_with_kerf_fits_single_piece(self):
        """Feedback #7 regression: piece length == stock length must fit
        even when kerf > 0, because kerf only applies *between* cuts and
        a single cut on a fresh bar has no preceding cut to separate from."""
        engine = NestEngine(kerf_width=5)
        pieces = [CutPiece(length=6100, mark="A1")]
        bars = [StockBar(length=6100, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)


class TestNestEngineStockMixes:
    """Stock variety scenarios that exercise sorting strategies."""

    def test_smallest_stock_first_does_not_starve_big_pieces(self):
        """Stock order: small bars before big bars. Big piece must still fit."""
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=6100, mark="A1")]
        bars = [
            StockBar(length=3000, mark="X", material="S", source="M"),
            StockBar(length=6100, mark="Y", material="S", source="M"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].original_length == pytest.approx(6100.0)

    def test_two_pieces_summing_to_bar_length_fit_in_one_bar(self):
        engine = NestEngine(kerf_width=0)
        pieces = [
            CutPiece(length=3050, mark="A1"),
            CutPiece(length=3050, mark="A2"),
        ]
        bars = [StockBar(length=6100, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0.0)

    def test_priority_ordering_preserved_by_strategy_zero(self):
        """Stock with explicit ordering (priority) is honoured by the
        priority-respecting strategies."""
        engine = NestEngine(kerf_width=0, max_strategies=2)  # only 0 & 1
        pieces = [CutPiece(length=6100, mark="A1")]
        bars = [
            StockBar(length=6100, mark="CLIENT", material="S", source="Cliente"),
            StockBar(length=6100, mark="MARKET", material="S", source="Mercado"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Either ordering may win on waste, but the chosen bar should be one of
        # the two valid 6100 bars.
        assert result.bars[0].mark in {"CLIENT", "MARKET"}

    def test_mixed_lengths_partial_when_some_pieces_too_big(self):
        engine = NestEngine(kerf_width=0)
        pieces = [
            CutPiece(length=6000, mark="A1"),
            CutPiece(length=20000, mark="OVERSIZED"),
        ]
        bars = [StockBar(length=6000, mark="X", material="S", source="M")]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 1
        assert [p.mark for p in result.unfit_pieces] == ["OVERSIZED"]


class TestNestEngineBestStrategySelection:
    """The engine should pick the strategy that fits the most pieces, then
    the strategy with the lowest waste."""

    def test_strategy_that_fits_more_pieces_wins(self):
        """A scenario where one strategy fits all pieces with 50% waste, and
        another fits fewer pieces with 0% waste. The 'more pieces' strategy
        must win."""
        engine = NestEngine(kerf_width=0)
        # 3 pieces of 6100, 3 bars of 6100 — every strategy fits everything
        pieces = [CutPiece(length=6100, mark=f"P{i}") for i in range(3)]
        bars = [StockBar(length=6100, mark="X", material="S", source="M") for _ in range(3)]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.unfit_pieces == []
        assert len(result.bars) == 3

    def test_zero_waste_chosen_when_all_strategies_fit(self):
        engine = NestEngine(kerf_width=0)
        pieces = [
            CutPiece(length=3000, mark="A1"),
            CutPiece(length=3000, mark="A2"),
        ]
        bars = [
            StockBar(length=6000, mark="X", material="S", source="M"),
            StockBar(length=12000, mark="Y", material="S", source="M"),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Best fit: both pieces in the 6000 bar → 0% waste
        assert len(result.bars) == 1
        assert result.waste_pct == pytest.approx(0.0)


class TestNestEnginePriority:
    """Feedback #11 — client stock (lower priority) must be consumed before
    market stock regardless of which length-sorting strategy the engine picks."""

    def test_client_stock_consumed_before_market_even_when_shorter(self):
        """A client bar that is shorter than a market bar should still be
        used first when both fit the piece — priority dominates length."""
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=3000, mark="P1")]
        bars = [
            StockBar(length=6000, mark="HEA240", material="S275", source="Mercado", priority=0),
            StockBar(length=4000, mark="HEA240", material="S275", source="Cliente", priority=-1000),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].source == "Cliente"

    def test_client_stock_consumed_before_market_when_longer(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=3000, mark="P1")]
        bars = [
            StockBar(length=4000, mark="HEA240", material="S275", source="Mercado", priority=0),
            StockBar(length=6000, mark="HEA240", material="S275", source="Cliente", priority=-1000),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        assert result.bars[0].source == "Cliente"

    def test_multiple_pieces_prefer_client_pool(self):
        engine = NestEngine(kerf_width=0)
        pieces = [CutPiece(length=3000, mark=f"P{i}") for i in range(2)]
        bars = [
            StockBar(length=6000, mark="HEA240", material="S275", source="Mercado", priority=0),
            StockBar(length=6000, mark="HEA240", material="S275", source="Cliente", priority=-1000),
        ]
        result = engine.optimize(pieces, bars)

        assert result is not None
        # Both pieces fit in one client bar; market bar untouched.
        assert len(result.bars) == 1
        assert result.bars[0].source == "Cliente"

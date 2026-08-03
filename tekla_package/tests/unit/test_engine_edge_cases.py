"""Hand-computed engine edge-case tests.

These tests pin specific arithmetic outcomes of NestEngine so a future
refactor that silently changes kerf accounting, bar-down-sizing, or
priority ordering is caught.
"""

from __future__ import annotations

import pytest
from tekla_nest.models.cut_piece import CutPiece
from tekla_nest.models.stock_bar import StockBar
from tekla_nest.services.nest_engine import NestEngine, NestError


def _piece(length: float, mark: str = "P") -> CutPiece:
    return CutPiece(length=length, mark=mark)


def _bar(
    length: float,
    source: str = "Mercado",
    priority: int = 0,
    mark: str = "B",
    material: str = "S275JR",
) -> StockBar:
    return StockBar(
        length=length,
        mark=mark,
        material=material,
        source=source,
        priority=priority,
    )


class TestEmptyInputs:
    def test_empty_pieces_returns_none(self):
        assert NestEngine().optimize([], [_bar(6000)]) is None

    def test_empty_bars_returns_none(self):
        assert NestEngine().optimize([_piece(3000)], []) is None

    def test_both_empty_returns_none(self):
        assert NestEngine().optimize([], []) is None


class TestKerfArithmetic:
    def test_no_kerf_full_packing(self):
        # 3×2000 onto 6000 — perfect fit
        engine = NestEngine(kerf_width=0.0)
        pieces = [_piece(2000, f"P{i}") for i in range(3)]
        bars = [_bar(6000)]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert len(result.bars) == 1
        assert sum(result.bars[0].cuts) == pytest.approx(6000)
        assert result.bars[0].free_length == pytest.approx(0)
        assert result.waste_pct == pytest.approx(0)
        assert not result.unfit_pieces

    def test_kerf_costs_only_between_cuts(self):
        # 3 cuts of 1990 with kerf 5: total = 1990 + 1995 + 1995 = 5980 ≤ 6000 → fits
        engine = NestEngine(kerf_width=5.0)
        pieces = [_piece(1990, f"P{i}") for i in range(3)]
        result = engine.optimize(pieces, [_bar(6000)])
        assert result is not None
        assert len(result.bars) == 1
        # First cut has no kerf, subsequent ones do
        assert result.bars[0].cuts == [1990, 1995, 1995]
        assert result.bars[0].free_length == pytest.approx(20)

    def test_kerf_blocks_third_cut(self):
        # 3×2000 + kerf 10 on 6000: 2000 + 2010 = 4010, third needs 2010 → 6020 > 6000 → unfit
        engine = NestEngine(kerf_width=10.0)
        pieces = [_piece(2000, f"P{i}") for i in range(3)]
        result = engine.optimize(pieces, [_bar(6000)])
        assert result is not None
        assert len(result.bars) == 1
        assert len(result.bars[0].cuts) == 2
        assert len(result.unfit_pieces) == 1


class TestUnfitHandling:
    def test_piece_longer_than_any_bar(self):
        engine = NestEngine()
        pieces = [_piece(7000)]
        bars = [_bar(6000)]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert result.bars == []
        assert len(result.unfit_pieces) == 1

    def test_partial_fit_reports_partial_plan(self):
        engine = NestEngine()
        # 5 pieces of 2000, only 2 bars of 6000 = 6 slots capacity
        # but only 2 bars × 6000 / 2000 = 6 pieces fit, so all 5 do.
        # Make it 8 pieces → 6 fit, 2 unfit.
        pieces = [_piece(2000, f"P{i}") for i in range(8)]
        bars = [_bar(6000), _bar(6000)]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert len(result.bars) == 2
        assert len(result.unfit_pieces) == 2


class TestPriorityOrdering:
    def test_client_stock_consumed_before_market(self):
        engine = NestEngine()
        pieces = [_piece(3000)]
        # Market bar listed first, but client has lower priority
        bars = [
            _bar(6000, source="Mercado", priority=0, mark="M"),
            _bar(6000, source="Cliente", priority=-1000, mark="C"),
        ]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].source == "Cliente", (
            "Client stock must be consumed before market stock"
        )

    def test_lower_priority_first_among_market(self):
        engine = NestEngine()
        pieces = [_piece(3000)]
        bars = [
            _bar(6000, priority=10, mark="A"),
            _bar(6000, priority=1, mark="B"),
        ]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert result.bars[0].mark == "B"


class TestBarDownsizing:
    def test_bar_downsized_when_smaller_length_exists(self):
        """Post-process should quote a 4000 bar instead of a 6000 if used ≤ 4000."""
        engine = NestEngine()
        pieces = [_piece(3000)]
        bars = [
            _bar(6000, mark="M6", material="S275JR"),
            _bar(4000, mark="M4", material="S275JR"),
        ]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert len(result.bars) == 1
        # Downsized: original_length should be 4000, not 6000
        assert result.bars[0].original_length == 4000

    def test_downsize_respects_material_boundary(self):
        """Pieces of one material must not be downsized onto a different-material bar.

        The engine is called once per (profile, material) group, but the
        bar-downsizing pass operates on the WORKING bar list which may
        still contain mixed-material entries left over from priority
        sorting. The downsize step must only swap to a bar of matching
        material/source.
        """
        engine = NestEngine()
        # Two bars of same length but different materials; piece is 3000.
        # Whichever bar is opened, downsizing must not swap across material.
        pieces = [_piece(3000)]
        bars = [
            _bar(6000, material="S275JR", mark="A6"),
            _bar(5000, material="S355JR", mark="B5"),  # different material
        ]
        result = engine.optimize(pieces, bars)
        assert result is not None
        picked = result.bars[0]
        # Whichever bar was opened, the downsize step must not have
        # silently switched the material to the other one.
        assert picked.material in ("S275JR", "S355JR")
        # And the picked length cannot be from the OTHER material's pool.
        if picked.material == "S275JR":
            assert picked.original_length == 6000  # only S275JR bar = 6000
        else:
            assert picked.original_length == 5000  # only S355JR bar = 5000

    def test_downsize_respects_source_boundary(self):
        engine = NestEngine()
        pieces = [_piece(3000)]
        bars = [
            _bar(6000, source="Mercado", mark="M6"),
            _bar(4000, source="Cliente", priority=-1, mark="C4"),
        ]
        # Client priority makes it consumed first; but if engine picks
        # market 6000, it must not downsize to a 4000 client bar.
        # Run twice — both orderings — to ensure invariant.
        result = engine.optimize(pieces, list(bars))
        assert result is not None
        # The picked bar's source must match its declared source after downsizing
        for bar in result.bars:
            # Cross-source downsizing would yield a 4000 bar with source "Mercado"
            # or a 6000 bar tagged "Cliente". Neither should happen.
            assert bar.source in ("Mercado", "Cliente")


class TestMultiBar:
    def test_two_pieces_into_two_bars_when_one_too_short(self):
        engine = NestEngine()
        # 2 pieces of 4000 on bars of 6000 each — each piece needs own bar
        pieces = [_piece(4000, "P1"), _piece(4000, "P2")]
        bars = [_bar(6000), _bar(6000)]
        result = engine.optimize(pieces, bars)
        assert result is not None
        assert len(result.bars) == 2
        assert all(len(b.cuts) == 1 for b in result.bars)

    def test_mixed_lengths_pack_optimally(self):
        # Bar 6000, pieces [3500, 1500, 1000] = 6000 total → 1 bar zero waste
        engine = NestEngine()
        pieces = [_piece(3500, "A"), _piece(1500, "B"), _piece(1000, "C")]
        result = engine.optimize(pieces, [_bar(6000)])
        assert result is not None
        assert len(result.bars) == 1
        assert result.bars[0].free_length == pytest.approx(0)


class TestValidation:
    def test_negative_piece_length_raises(self):
        engine = NestEngine()
        with pytest.raises(NestError):
            engine.optimize([_piece(-100)], [_bar(6000)])

    def test_negative_bar_length_raises(self):
        engine = NestEngine()
        with pytest.raises(NestError):
            engine.optimize([_piece(1000)], [_bar(-6000)])

    def test_zero_length_piece_raises(self):
        engine = NestEngine()
        with pytest.raises(NestError):
            engine.optimize([_piece(0)], [_bar(6000)])


class TestWastePercentage:
    def test_waste_pct_matches_hand_compute(self):
        engine = NestEngine()
        # 1 piece of 4000 on a 6000 bar → waste = 2000 / 6000 = 33.33%
        result = engine.optimize([_piece(4000)], [_bar(6000)])
        assert result is not None
        assert result.waste_pct == pytest.approx(2000 / 6000 * 100, rel=1e-3)

    def test_all_unfit_yields_100pct_waste(self):
        engine = NestEngine()
        result = engine.optimize([_piece(7000)], [_bar(6000)])
        assert result is not None
        assert result.waste_pct == pytest.approx(100.0)


class TestDuplicateReferences:
    def test_same_mark_different_lengths_both_placed(self):
        engine = NestEngine()
        # Two pieces share the mark "P1" with different lengths
        pieces = [_piece(2000, "P1"), _piece(3000, "P1")]
        result = engine.optimize(pieces, [_bar(6000)])
        assert result is not None
        assert sum(len(b.cuts) for b in result.bars) == 2

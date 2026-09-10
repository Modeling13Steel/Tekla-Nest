"""Core 1D bin-packing optimizer using multi-strategy First Fit Decreasing.

Migrated from: C# FrmNest.otimizar() + CalculateCuts()
All static mutable state eliminated — everything is instance or local.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import BarResult, CutPiece, ProfileResult, StockBar


@dataclass
class NestEngine:
    """1D bin-packing optimizer.

    Usage::

        engine = NestEngine(kerf_width=5.0)
        result = engine.optimize(pieces, bars)
    """

    kerf_width: float = 0.0
    scrap_threshold: float = 2000.0
    max_strategies: int = 6

    def optimize(
        self,
        pieces: list[CutPiece],
        bars: list[StockBar],
    ) -> ProfileResult | None:
        """Run multi-strategy optimization.

        Args:
            pieces: Expanded list of desired cuts (one per physical piece).
            bars:   Expanded list of available stock bars (one per physical bar),
                    pre-sorted by priority.

        Returns:
            ProfileResult with the best solution found across strategies. If
            no piece could be fitted in any strategy, the result will have
            empty ``bars`` and all pieces listed in ``unfit_pieces``.
            Returns None only when ``pieces`` or ``bars`` is empty.

        Raises:
            NestError: If inputs are structurally invalid (negative lengths, etc.).
        """
        if not pieces or not bars:
            return None

        self._validate_inputs(pieces, bars)

        strategy_count = min(self.max_strategies, 6)
        solutions: list[_Solution] = []

        for strategy_idx in range(strategy_count):
            sorted_pieces = self._sort_pieces(pieces, strategy_idx)
            sorted_bars = self._sort_bars(list(bars), strategy_idx)

            result_bars, unfit = self._calculate_cuts(sorted_pieces, sorted_bars)

            total_stock = sum(b.original_length for b in result_bars)
            total_waste = sum(b.free_length for b in result_bars)
            scrap_waste = sum(
                b.free_length for b in result_bars
                if b.free_length <= self.scrap_threshold
            )

            if total_stock > 0:
                waste_pct = (total_waste / total_stock) * 100.0
                scrap_pct = (scrap_waste / total_stock) * 100.0
            else:
                waste_pct = 100.0 if unfit else 0.0
                scrap_pct = 0.0

            last_remnant = result_bars[-1].free_length if result_bars else 0.0
            solutions.append(_Solution(
                bars=sorted(result_bars, key=lambda b: b.free_length),
                waste_pct=waste_pct,
                scrap_pct=scrap_pct,
                last_remnant=last_remnant,
                unfit=list(unfit),
            ))

        if not solutions:
            return None

        best = min(
            solutions,
            key=lambda s: (
                len(s.unfit),
                # Feedback #11 — prefer solutions that consume the
                # highest-priority stock (most-negative priority value).
                # Sum priorities of bars actually used: lower sum = more
                # client/priority bars used.
                sum(b.priority for b in s.bars),
                s.waste_pct,
                -s.last_remnant,
            ),
        )

        return ProfileResult(
            profile="",
            bars=best.bars,
            waste_pct=best.waste_pct,
            scrap_pct=best.scrap_pct,
            unfit_pieces=best.unfit,
        )

    # ── Sorting strategies ───────────────────────────────────

    @staticmethod
    def _sort_pieces(pieces: list[CutPiece], strategy: int) -> list[CutPiece]:
        """6 sorting strategies for desired cuts.

        Migrated from: the if/else chain in otimizar() loop.
        """
        if strategy in (0, 2, 3):
            return sorted(pieces, key=lambda p: p.length)
        elif strategy in (1, 4, 5):
            return sorted(pieces, key=lambda p: p.length, reverse=True)
        return list(pieces)

    @staticmethod
    def _sort_bars(bars: list[StockBar], strategy: int) -> list[StockBar]:
        """Bar sorting per strategy — priority always wins, length is the tie-breaker.

        Migrated from: PossibleLengths re-sorting in otimizar().

        Feedback #11: client stock (priority < 0) must be consumed before
        market stock regardless of the length-sort direction; otherwise
        downsizing strategies silently prefer shorter market bars over
        equally-suitable client bars. We honour priority first, length
        second, in every strategy.
        """
        if strategy in (2, 4):
            return sorted(bars, key=lambda b: (b.priority, b.length))
        elif strategy in (3, 5):
            return sorted(bars, key=lambda b: (b.priority, -b.length))
        # Strategies 0 and 1: keep caller's priority order, no length sort.
        return list(bars)

    # ── Core bin-packing ─────────────────────────────────────

    def _calculate_cuts(
        self,
        pieces: list[CutPiece],
        available: list[StockBar],
    ) -> tuple[list[BarResult], list[CutPiece]]:
        """Modified First Fit Decreasing bin-packing.

        Returns:
            (result_bars, unfit_pieces). ``unfit_pieces`` is non-empty when
            available stock cannot accommodate every piece. The algorithm
            still returns whatever bars were successfully filled so callers
            can show a partial plan.

        Kerf model (feedback #7): the saw kerf consumes material *between*
        cuts, not on every cut. The first cut on a bar therefore does not
        carry a kerf allowance; subsequent cuts do. This makes the equality
        case (piece length == stock length, kerf > 0) fit cleanly when only
        a single cut is required.
        """
        available = list(available)  # work on a copy
        result_bars: list[BarResult] = []
        unfit_pieces: list[CutPiece] = []

        for piece in pieces:
            # Fitting onto an already-opened bar means a fresh cut after
            # an existing one, so we must reserve one kerf width — but
            # only the piece's own length is recorded in ``cuts`` (kerf
            # is tracked separately) so exports show the real cut length.
            needed_with_kerf = piece.length + self.kerf_width

            fit_bar = next(
                (b for b in result_bars if b.free_length >= needed_with_kerf),
                None,
            )
            if fit_bar is not None:
                fit_bar.cuts.append(piece.length)
                fit_bar.cut_marks.append(piece.mark)
                fit_bar.kerf_used += self.kerf_width
                continue

            # Opening a new bar: the very first cut has no preceding cut,
            # so no kerf allowance applies — only the piece itself.
            placed = False
            while available:
                new_stock = available.pop(0)
                if new_stock.length >= piece.length:
                    new_bar = BarResult(
                        original_length=new_stock.length,
                        mark=new_stock.mark,
                        material=new_stock.material,
                        source=new_stock.source,
                        priority=new_stock.priority,
                    )
                    new_bar.cuts.append(piece.length)
                    new_bar.cut_marks.append(piece.mark)
                    result_bars.append(new_bar)
                    placed = True
                    break

            if not placed:
                unfit_pieces.append(piece)

        # Post-process: try downsizing bars to smaller available lengths
        # within the same source/material so a 6000 mm bar marked
        # "Mercado / S275" can be quoted as 4000 mm if such a purchase
        # length exists. Crossing source or material would silently
        # re-attribute the bar and confuse the purchase report
        # (feedback #11 — the engine must keep client/market distinct).
        # The matched stock entry is removed from ``available`` so a
        # single physical piece of stock can't be "reused" as the
        # downsize target for more than one bar.
        for bar in result_bars:
            best_length = bar.original_length
            best_stock: StockBar | None = None
            for stock in available:
                if (
                    stock.source == bar.source
                    and stock.material == bar.material
                    and stock.length < best_length
                    and bar.used_length <= stock.length
                ):
                    best_length = stock.length
                    best_stock = stock
            if best_stock is not None:
                bar.original_length = best_length
                available.remove(best_stock)

        return result_bars, unfit_pieces

    # ── Input validation ─────────────────────────────────────

    @staticmethod
    def _validate_inputs(
        pieces: list[CutPiece], bars: list[StockBar]
    ) -> None:
        """Check for structurally invalid inputs."""
        for i, p in enumerate(pieces):
            if p.length <= 0:
                raise NestError(
                    f"Piece at index {i} (mark={p.mark!r}) has invalid "
                    f"length={p.length}. Length must be > 0."
                )
        for i, b in enumerate(bars):
            if b.length <= 0:
                raise NestError(
                    f"Stock bar at index {i} (mark={b.mark!r}) has invalid "
                    f"length={b.length}. Length must be > 0."
                )


class NestError(Exception):
    """Raised when the nesting algorithm encounters invalid data.

    Messages always describe what's wrong, where, and what's expected.
    """


@dataclass
class _Solution:
    """Internal: one candidate solution from a single strategy."""

    bars: list[BarResult]
    waste_pct: float
    scrap_pct: float
    last_remnant: float
    unfit: list[CutPiece] = field(default_factory=list)

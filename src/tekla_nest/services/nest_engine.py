"""1D cutting optimizer for one (profile, material) group.

``NestEngine.optimize`` groups pieces into length types and stock into
types, then runs the multiple-stock-size cutting stock portfolio in
:mod:`.cutting_stock` (column-generation LP bound, residual rounding, exact
search for small instances / residuals, 2-3 bar exact local search). The
legacy multi-strategy First Fit Decreasing (migrated from C#
FrmNest.otimizar() + CalculateCuts()) still runs as a seed candidate.

Objective, lexicographic: fewest unfit pieces; least purchased (non
"Cliente") stock length -- client stock is free; fewest bars; lowest
priority sum; least stock length; least scrap; biggest reusable offcuts.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..models import BarResult, CutPiece, ProfileResult, StockBar
from .cutting_stock import EPS, CuttingStock, Stock

CLIENT_SOURCE = "Cliente"


@dataclass
class NestEngine:
    """1D cutting stock optimizer.

    Usage::

        engine = NestEngine(kerf_width=5.0)
        result = engine.optimize(pieces, bars)
        engine.last_lower_bound    # LP bound on purchased mm (None if unknown)
        engine.last_proven_optimal # True when the plan provably hits the optimum
    """

    kerf_width: float = 0.0
    scrap_threshold: float = 2000.0
    max_strategies: int = 6
    last_lower_bound: float | None = field(default=None, init=False, compare=False)
    last_proven_optimal: bool = field(default=False, init=False, compare=False)

    def optimize(
        self,
        pieces: list[CutPiece],
        bars: list[StockBar],
    ) -> ProfileResult | None:
        """Find the cheapest cut plan.

        Args:
            pieces: Expanded list of desired cuts (one per physical piece).
            bars:   Expanded list of available stock bars (one per physical
                    bar). Each result bar takes the length/mark/material/
                    source/priority of one of these, and quantities are
                    respected.

        Returns:
            ProfileResult with the best plan. Pieces longer than every bar,
            or left over when stock runs out, are listed in ``unfit_pieces``
            next to the partial plan. Returns None only when ``pieces`` or
            ``bars`` is empty.

        Raises:
            NestError: If inputs are structurally invalid (negative lengths, etc.).
        """
        self.last_lower_bound = None
        self.last_proven_optimal = False
        if not pieces or not bars:
            return None

        self._validate_inputs(pieces, bars)
        k = self.kerf_width

        # Stock types, in preference order (free first, then priority, length).
        groups: dict[tuple, list] = {}
        for i, b in enumerate(bars):
            g = groups.setdefault((b.length, b.mark, b.material, b.source, b.priority), [b, 0, i])
            g[1] += 1
        reps = sorted(
            groups.values(),
            key=lambda g: (self._cost(g[0]), g[0].priority, g[0].length, g[2]),
        )
        stock_bars = [g[0] for g in reps]
        stocks = [Stock(b.length + k, self._cost(b), q, b.priority, b.length)
                  for b, q, _ in reps]

        # Piece types by length, longest first; marks are re-attached at the end.
        max_len = max(b.length for b in bars)
        queues: dict[float, deque[int]] = {}  # length -> piece indices, input order
        oversize: list[int] = []
        for i, p in enumerate(pieces):
            if p.length > max_len + EPS:
                oversize.append(i)
            else:
                queues.setdefault(p.length, deque()).append(i)
        lengths = sorted(queues, reverse=True)
        type_of = {L: t for t, L in enumerate(lengths)}

        plan: list = []
        if lengths:
            solver = CuttingStock(
                [L + k for L in lengths],
                [len(queues[L]) for L in lengths],
                stocks,
                self.scrap_threshold,
            )
            seeds = []
            fitting = [p for p in pieces if p.length <= max_len + EPS]
            for strategy_idx in range(min(self.max_strategies, 6)):
                legacy, _ = self._calculate_cuts(
                    self._sort_pieces(fitting, strategy_idx),
                    self._sort_bars(list(bars), strategy_idx),
                )
                pats = []
                for b in legacy:
                    pat = [0] * len(lengths)
                    for c in b.cuts:
                        pat[type_of[c]] += 1
                    pats.append(tuple(pat))
                seeds.append(pats)
            plan, _ = solver.solve(seeds)
            self.last_lower_bound = solver.lower_bound
            self.last_proven_optimal = solver.proven_optimal  # over-length pieces aside

        result_bars: list[BarResult] = []
        for j, pat in plan:
            sb = stock_bars[j]
            bar = BarResult(
                original_length=sb.length,
                mark=sb.mark,
                material=sb.material,
                source=sb.source,
                priority=sb.priority,
            )
            for t, a in enumerate(pat):
                for _ in range(a):
                    piece = pieces[queues[lengths[t]].popleft()]
                    bar.cuts.append(piece.length)
                    bar.cut_marks.append(piece.mark)
            bar.kerf_used = k * (len(bar.cuts) - 1)
            result_bars.append(bar)
        result_bars.sort(key=lambda b: b.free_length)

        unfit = [pieces[i] for i in sorted(oversize + [i for q in queues.values() for i in q])]

        total_stock = sum(b.original_length for b in result_bars)
        total_waste = sum(b.free_length for b in result_bars)
        scrap_waste = sum(
            b.free_length for b in result_bars
            if b.free_length <= self.scrap_threshold
        )
        if total_stock > 0:
            waste_pct = total_waste / total_stock * 100.0
            scrap_pct = scrap_waste / total_stock * 100.0
        else:
            waste_pct = 100.0 if unfit else 0.0
            scrap_pct = 0.0

        return ProfileResult(
            profile="",
            bars=result_bars,
            waste_pct=waste_pct,
            scrap_pct=scrap_pct,
            unfit_pieces=unfit,
        )

    @staticmethod
    def _cost(bar: StockBar) -> float:
        """Purchase cost: client stock is already in the yard."""
        return 0.0 if bar.source == CLIENT_SOURCE else bar.length

    # ── Legacy FFD (seed candidates) ─────────────────────────

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
        free: list[float] = []  # free length per result bar (kept in step)

        for piece in pieces:
            # Fitting onto an already-opened bar means a fresh cut after
            # an existing one, so we must reserve one kerf width — but
            # only the piece's own length is recorded in ``cuts`` (kerf
            # is tracked separately) so exports show the real cut length.
            needed_with_kerf = piece.length + self.kerf_width

            fit = next(
                (i for i, f in enumerate(free) if f >= needed_with_kerf),
                None,
            )
            if fit is not None:
                fit_bar = result_bars[fit]
                fit_bar.cuts.append(piece.length)
                fit_bar.cut_marks.append(piece.mark)
                fit_bar.kerf_used += self.kerf_width
                free[fit] -= needed_with_kerf
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
                    free.append(new_stock.length - piece.length)
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

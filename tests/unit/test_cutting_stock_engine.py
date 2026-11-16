"""Optimality tests for the cutting-stock NestEngine (exactness, client stock,
kerf, determinism, unfit handling, lower bound)."""
from __future__ import annotations

import random
import time
from collections import Counter
from itertools import product

import pytest

from tekla_nest.models import CutPiece, StockBar
from tekla_nest.services.nest_engine import NestEngine

HOT = [6100, 10100, 12100, 14100, 15100, 16100]


def market(lengths=HOT, qty=100, material="S275JR"):
    return [StockBar(L, "HEA240", material, "Mercado") for L in lengths for _ in range(qty)]


def client(length, qty, material="S275JR"):
    return [StockBar(length, "HEA240", material, "Cliente", priority=-1000) for _ in range(qty)]


def pieces(*lengths):
    return [CutPiece(L, f"P{i}") for i, L in enumerate(lengths)]


def bought(result):
    return sum(b.original_length for b in result.bars if b.source != "Cliente")


def check_plan(result, pcs, stock, kerf):
    """Invariants: every piece once, no overfill, kerf between cuts, stock qty kept."""
    placed = Counter((c, m) for b in result.bars for c, m in zip(b.cuts, b.cut_marks, strict=True))
    placed.update((p.length, p.mark) for p in result.unfit_pieces)
    assert placed == Counter((p.length, p.mark) for p in pcs)
    have = Counter((s.length, s.mark, s.material, s.source, s.priority) for s in stock)
    used = Counter((b.original_length, b.mark, b.material, b.source, b.priority)
                   for b in result.bars)
    assert all(used[k] <= have[k] for k in used), "stock quantity exceeded / invented bar"
    for b in result.bars:
        assert b.kerf_used == pytest.approx(kerf * (len(b.cuts) - 1))
        assert b.used_length <= b.original_length + 1e-6


def brute_force(lengths, stock_lengths, kerf):
    """Min purchased length by trying every assignment of pieces to <= n bars."""
    n = len(lengths)
    best = float("inf")
    for assign in product(range(n), repeat=n):
        if any(assign[i] > max(assign[:i], default=-1) + 1 for i in range(n)):
            continue  # canonical labelling only
        total = 0.0
        for b in set(assign):
            cut = [lengths[i] for i in range(n) if assign[i] == b]
            need = sum(cut) + kerf * (len(cut) - 1)
            fit = [L for L in stock_lengths if need <= L]
            if not fit:
                break
            total += min(fit)
        else:
            best = min(best, total)
    return best


class TestExactness:
    def test_reported_customer_case_two_16100(self):
        """Old engine bought 14100+12100+10100 = 36.3 m; optimum is 2 x 16100."""
        e = NestEngine(kerf_width=3)
        pcs = pieces(6365, 5775, 5775, 4715, 3140, 1860, 1860, 1195, 1195)
        r = e.optimize(pcs, market())
        check_plan(r, pcs, market(), 3)
        assert sorted(b.original_length for b in r.bars) == [16100, 16100]
        assert e.last_proven_optimal
        assert e.last_lower_bound <= 32200 + 1e-6

    def test_merges_two_short_bars_into_one(self):
        e = NestEngine(kerf_width=0)
        r = e.optimize(pieces(6000, 6000), market())
        assert [b.original_length for b in r.bars] == [12100]

    @pytest.mark.parametrize("seed", range(12))
    @pytest.mark.parametrize("kerf", [0, 3])
    def test_matches_brute_force_on_small_random(self, seed, kerf):
        rng = random.Random(seed)
        lens = [float(rng.randint(300, 9000) // 5 * 5) for _ in range(rng.randint(2, 6))]
        e = NestEngine(kerf_width=kerf)
        pcs = [CutPiece(L, f"P{i}") for i, L in enumerate(lens)]
        r = e.optimize(pcs, market())
        check_plan(r, pcs, market(), kerf)
        assert bought(r) == pytest.approx(brute_force(lens, HOT, kerf))
        assert e.last_proven_optimal


class TestClientStock:
    def test_client_offcuts_take_the_right_pieces(self):
        """Eval client#3: free 4500 offcuts must carry the 3830s, not the 2665s."""
        e = NestEngine(kerf_width=3)
        pcs = [CutPiece(L, m) for L, m, q in [
            (3830, "A", 2), (3180, "B", 1), (2665, "C", 2), (7070, "D", 2), (3440, "E", 1)
        ] for _ in range(q)]
        stock = client(4500, 2) + market()
        r = e.optimize(pcs, stock)
        check_plan(r, pcs, stock, 3)
        assert bought(r) == 27200
        assert sum(b.source == "Cliente" for b in r.bars) == 2
        assert e.last_proven_optimal

    def test_limited_client_quantity_respected(self):
        e = NestEngine()
        pcs = pieces(*[5000] * 5)
        stock = client(6000, 2) + market([6100])
        r = e.optimize(pcs, stock)
        check_plan(r, pcs, stock, 0)
        assert sum(b.source == "Cliente" for b in r.bars) == 2
        assert bought(r) == 3 * 6100

    def test_client_stock_only_partial_plan(self):
        e = NestEngine()
        pcs = pieces(4000, 4000, 4000, 1500)
        stock = client(6000, 2)
        r = e.optimize(pcs, stock)
        check_plan(r, pcs, stock, 0)
        assert len(r.bars) == 2
        assert len(r.unfit_pieces) == 1  # 4000+1500 and 4000 placed, one 4000 left

    def test_unused_client_bar_never_beaten_by_purchase(self):
        e = NestEngine()
        pcs = pieces(9000, 2000)
        stock = market() + client(9500, 1)
        r = e.optimize(pcs, stock)
        assert bought(r) == 6100  # 9000 on the free 9500, 2000 on a 6100
        assert any(b.source == "Cliente" and b.cuts == [9000] for b in r.bars)


class TestKerfEdges:
    def test_exact_fill_with_kerf(self):
        # 3 x 2030 + 2 kerfs of 5 = 6100 fits exactly; 3 x 2031 needs 6103.
        e = NestEngine(kerf_width=5)
        assert len(e.optimize(pieces(2030, 2030, 2030), market([6100])).bars) == 1
        assert len(e.optimize(pieces(2031, 2031, 2031), market([6100])).bars) == 2

    def test_single_piece_equal_to_stock_with_kerf(self):
        e = NestEngine(kerf_width=5)
        r = e.optimize(pieces(16100), market())
        assert [b.original_length for b in r.bars] == [16100]
        assert r.bars[0].free_length == pytest.approx(0)


class TestUnfit:
    def test_over_length_mixed_with_normal_pieces(self):
        e = NestEngine(kerf_width=3)
        pcs = pieces(17000, 5000, 5000)
        r = e.optimize(pcs, market())
        check_plan(r, pcs, market(), 3)
        assert [p.length for p in r.unfit_pieces] == [17000]
        assert [b.original_length for b in r.bars] == [10100]

    def test_stock_exhausted_places_as_many_as_possible(self):
        e = NestEngine()
        pcs = pieces(*[3000] * 5, 7000)
        stock = market([6000], qty=2) + market([7000], qty=1)
        r = e.optimize(pcs, stock)
        check_plan(r, pcs, stock, 0)
        assert len(r.unfit_pieces) == 1


class TestDeterminismAndScale:
    def _big(self, seed=0, marks=40, qty=12):
        rng = random.Random(seed)
        pcs = []
        for m in range(marks):
            L = float(rng.randint(300, 12000) // 5 * 5)
            pcs += [CutPiece(L, f"M{m}") for _ in range(rng.randint(1, qty))]
        return pcs

    def test_same_input_same_plan(self):
        pcs = self._big()
        a = NestEngine(kerf_width=3).optimize(pcs, market())
        b = NestEngine(kerf_width=3).optimize(list(pcs), market())
        def sig(r):
            return [(x.original_length, x.cuts, x.cut_marks) for x in r.bars]

        assert sig(a) == sig(b)

    def test_large_instance_near_bound_and_fast(self):
        pcs = self._big(1, marks=40, qty=24)  # ~500 pieces, 40 lengths
        e = NestEngine(kerf_width=3)
        t = time.perf_counter()
        r = e.optimize(pcs, market())
        elapsed = time.perf_counter() - t
        check_plan(r, pcs, market(), 3)
        assert not r.unfit_pieces
        lb = e.last_lower_bound
        assert lb is not None and lb <= bought(r) + 1e-6
        assert (bought(r) - lb) / lb < 0.005  # within 0.5 % of the LP bound
        assert elapsed < 5.0  # generous: ~0.5 s on a laptop

    def test_materials_never_mixed(self):
        e = NestEngine()
        pcs = pieces(3000)
        stock = market([6000], material="S275JR") + market([5000], material="S355JR")
        r = e.optimize(pcs, stock)
        b = r.bars[0]
        assert (b.original_length, b.material) in {(6000, "S275JR"), (5000, "S355JR")}

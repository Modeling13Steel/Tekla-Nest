"""Regression gate for the nesting eval (see nest_eval.py).

Correctness invariants must hold on every instance. Optimality thresholds
are ratchets pinned just above the 2026-11 column-generation engine
(old FFD engine at b4c48c0 was 1-12% above optimum on small jobs, up to
28.7% with client offcuts):
tighten them when the engine improves, never loosen them to make a change
pass.

Fast part runs by default (~15 s). Heavy part (full-size projects, 30
seeds, MILP to 10 s per group):  uv run pytest tests/eval -m eval_slow
"""
from __future__ import annotations

from collections import Counter

import pytest

from tekla_nest.config.app_config import load_config, reset_config
from tests.eval.nest_eval import (
    make_instances,
    make_projects,
    make_realistic,
    optimal_purchase,
    run,
    summarize,
)
from tests.eval.reference import StockType, solve

# family -> (max mean gap to exact DP optimum %, max worst-case gap %)
RATCHET = {"short": (0.01, 0.01), "mixed": (0.01, 0.01), "long": (0.01, 0.01)}

# family -> (max mean gap to the reference lower bound %, max worst-case %)
LB_RATCHET = {
    "short": (0.01, 0.01),
    "mixed": (0.01, 0.01),
    "long": (0.01, 0.01),
    "big-mixed": (0.15, 0.3),
    "client": (0.01, 0.01),
    "frame-medium": (0.01, 0.01),
    "frame-offcuts-medium": (0.01, 0.01),
    "hall-medium": (0.01, 0.01),
    "hall-offcuts-medium": (0.01, 0.01),
    "multi-medium": (0.01, 0.01),
    "multi-offcuts-medium": (0.01, 0.01),
    "secondary-medium": (0.01, 0.01),
    "secondary-offcuts-medium": (0.01, 0.01),
    "project:synthetic-example": (0.01, 0.01),
}
LB_RATCHET_SLOW = {
    "short": (0.01, 0.01),
    "mixed": (0.01, 0.01),
    "long": (0.01, 0.01),
    "big-mixed": (0.1, 0.3),
    "client": (0.01, 0.01),
    "frame-full": (0.01, 0.05),
    "frame-offcuts-full": (0.01, 0.05),
    "hall-full": (0.02, 0.15),
    "hall-offcuts-full": (0.02, 0.05),
    "multi-full": (0.01, 0.03),
    "multi-offcuts-full": (0.01, 0.05),
    "secondary-full": (0.01, 0.01),
    "secondary-offcuts-full": (0.01, 0.06),
    "project:synthetic-example": (0.01, 0.01),
}


@pytest.fixture(scope="module")
def config():
    reset_config()
    load_config("config.yaml")
    yield
    reset_config()


@pytest.fixture(scope="module")
def scores(config):
    insts = make_instances(10) + make_realistic("medium", 3) + make_projects()
    return [run(i, kerf=3.0, time_limit=2.0) for i in insts]


@pytest.fixture(scope="module")
def slow_scores(config):
    insts = make_instances(30) + make_realistic("full", 3) + make_projects()
    return [run(i, kerf=3.0, time_limit=10.0) for i in insts]


def test_optimal_purchase_dp():
    # 3 x 6000 pieces: 16100 can't hold 3 (18000), so 12100 + 6100 is optimal.
    assert optimal_purchase([6000] * 3, [6100, 12100, 16100], 0) == 18200
    # kerf between cuts pushes 2 x 6050 past 12100 -> two 6100 bars.
    assert optimal_purchase([6050, 6050], [6100, 12100], 5) == 12200


def test_reference_small_cases():
    st = [StockType(L, L) for L in (6100, 12100, 16100)]
    r = solve([6000], [3], st)
    assert (r.lb, r.best, r.proven) == (18200, 18200, True)
    assert solve([6050], [2], [StockType(L, L) for L in (6100, 12100)], kerf=5).best == 12200
    # a free, limited client bar takes one piece
    r = solve([6000], [3], st + [StockType(6000, 0, 1)])
    assert (r.best, r.proven) == (12100, True)
    # trim: capacity 6000 but costed 6100
    assert solve([5990], [2], [StockType(6000, 6100)]).best == 12200


def test_reference_matches_subset_dp(config):
    """Exhaustive-pattern MILP must equal the subset DP; LB must not exceed it."""
    lengths = [6100, 10100, 12100, 14100, 15100, 16100]
    checked = 0
    for inst in make_instances(8):
        pieces = inst.pieces
        if inst.client or len(pieces) > 13:
            continue
        for kerf in (0.0, 4.0):
            opt = optimal_purchase(pieces, lengths, kerf)
            t = Counter(pieces)
            r = solve(list(t), list(t.values()), [StockType(L, L) for L in lengths], kerf)
            assert r.exact_milp and r.best == opt, (inst.name, kerf, r, opt)
            assert r.lb <= opt + 1e-6
            checked += 1
    assert checked >= 20


def test_correctness_invariants(scores):
    hard = [f"{s.name}: {v}" for s in scores for v in s.violations]
    assert not hard, "\n".join(hard)


def test_bounds_are_consistent(scores):
    for s in scores:
        assert s.lb_mm is not None and s.best_mm is not None, s.name
        assert s.lb_mm <= s.best_mm + 1e-6 <= s.purchased_mm + 2e-6, s


@pytest.mark.parametrize("family", sorted(RATCHET))
def test_gap_to_optimum_ratchet(scores, family):
    m = summarize(scores)[family]
    mean_max, worst_max = RATCHET[family]
    assert m["opt_gap_mean"] <= mean_max, m
    assert m["opt_gap_max"] <= worst_max, m


@pytest.mark.parametrize("family", sorted(LB_RATCHET))
def test_gap_to_lb_ratchet(scores, family):
    m = summarize(scores)[family]
    mean_max, worst_max = LB_RATCHET[family]
    assert m["lb_gap_mean"] <= mean_max, m
    assert m["lb_gap_max"] <= worst_max, m


def test_runtime_budget(scores):
    # Wall-clock per project (all profile groups), ~2x the measured max so
    # machine noise doesn't flake; the app runs this in a QThread.
    assert max(s.ms for s in scores) < 2500


def test_project_fixture_loader(scores):
    s = next(s for s in scores if s.family == "project:synthetic-example")
    assert s.pieces == 97 and s.competitor_mm == 477400
    assert s.unfit == 0 and s.lb_mm > 0


@pytest.mark.eval_slow
def test_slow_invariants_and_bounds(slow_scores):
    hard = [f"{s.name}: {v}" for s in slow_scores for v in s.violations]
    assert not hard, "\n".join(hard)
    for s in slow_scores:
        assert s.lb_mm <= s.best_mm + 1e-6 <= s.purchased_mm + 2e-6, s


@pytest.mark.eval_slow
@pytest.mark.parametrize("family", sorted(LB_RATCHET_SLOW))
def test_slow_gap_to_lb_ratchet(slow_scores, family):
    m = summarize(slow_scores)[family]
    mean_max, worst_max = LB_RATCHET_SLOW[family]
    assert m["lb_gap_mean"] <= mean_max, m
    assert m["lb_gap_max"] <= worst_max, m


@pytest.mark.eval_slow
def test_slow_runtime_budget(slow_scores):
    # ~3000-piece projects: p50 1-2.5 s, noisy max ~4.7 s on a laptop.
    assert max(s.ms for s in slow_scores) < 6000

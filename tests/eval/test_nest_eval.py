"""Regression gate for the nesting eval (see nest_eval.py).

Correctness invariants must hold on every instance. Optimality thresholds
are a ratchet pinned just above the 2026-11 baseline: tighten them when
the engine improves, never loosen them to make a change pass.
"""
from __future__ import annotations

import pytest

from tekla_nest.config.app_config import load_config, reset_config
from tests.eval.nest_eval import make_instances, optimal_purchase, run, summarize

# family -> (max mean gap to optimum %, max worst-case gap %)
RATCHET = {"short": (2.0, 10.0), "mixed": (3.5, 13.0), "long": (0.5, 5.0)}


@pytest.fixture(scope="module")
def scores():
    reset_config()
    load_config("config.yaml")
    yield [run(i, kerf=3.0) for i in make_instances(10)]
    reset_config()


def test_optimal_purchase_dp():
    # 3 x 6000 pieces: 16100 can't hold 3 (18000), so 12100 + 6100 is optimal.
    assert optimal_purchase([6000] * 3, [6100, 12100, 16100], 0) == 18200
    # kerf between cuts pushes 2 x 6050 past 12100 -> two 6100 bars.
    assert optimal_purchase([6050, 6050], [6100, 12100], 5) == 12200


def test_correctness_invariants(scores):
    hard = [
        f"{s.name}: {v}" for s in scores for v in s.violations
        if not v.startswith("mergeable")  # optimality smell, gated below
    ]
    assert not hard, "\n".join(hard)


@pytest.mark.parametrize("family", sorted(RATCHET))
def test_gap_to_optimum_ratchet(scores, family):
    m = summarize(scores)[family]
    mean_max, worst_max = RATCHET[family]
    assert m["opt_gap_mean"] <= mean_max, m
    assert m["opt_gap_max"] <= worst_max, m


def test_runtime_budget(scores):
    assert max(s.ms for s in scores) < 500

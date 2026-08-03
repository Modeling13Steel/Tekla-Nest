"""Unit tests for the shared bar_aggregation helper.

Covers the contract that the four export surfaces (CSV / Excel / PDF /
in-app purchase tab) all consume.
"""

from __future__ import annotations

import pytest
from tekla_nest.models.bar_result import BarResult
from tekla_nest.models.nest_result import NestResult, ProfileResult
from tekla_nest.services.bar_aggregation import (
    aggregate_prep,
    aggregate_purchase,
    available_scope_keys,
    filter_profiles,
    grand_totals,
)


def _bar(length, source="Mercado", material="S275JR", cuts=()):
    return BarResult(
        original_length=float(length),
        mark="b",
        material=material,
        source=source,
        cuts=list(cuts),
    )


def _result():
    return NestResult(
        profiles=[
            ProfileResult(
                profile="IPE200",
                material="S275JR",
                bars=[_bar(12000), _bar(12000), _bar(6000)],
            ),
            ProfileResult(
                profile="IPE200",
                material="S420",
                bars=[_bar(12000)],
            ),
            ProfileResult(
                profile="HEA300",
                material="S275JR",
                bars=[_bar(6000, source="Cliente"), _bar(6000, source="Cliente")],
            ),
        ]
    )


def test_aggregate_purchase_buckets_by_full_key():
    rows = aggregate_purchase(_result())
    # 3 distinct buckets: IPE200/S275JR/12000, IPE200/S275JR/6000,
    # IPE200/S420/12000, HEA300/S275JR/6000/Cliente
    assert len(rows) == 4
    by_key = {(r.profile, r.material, r.length): r for r in rows}
    assert by_key[("IPE200", "S275JR", 12000.0)].count == 2
    assert by_key[("IPE200", "S275JR", 6000.0)].count == 1
    assert by_key[("IPE200", "S420", 12000.0)].count == 1
    assert by_key[("HEA300", "S275JR", 6000.0)].count == 2


def test_aggregate_purchase_orders_length_desc_within_group():
    rows = aggregate_purchase(_result())
    ipe275 = [r for r in rows if r.profile == "IPE200" and r.material == "S275JR"]
    # Longest first — procurement workflow.
    assert [r.length for r in ipe275] == [12000.0, 6000.0]


def test_aggregate_purchase_respects_scope():
    scope = frozenset({("ipe200", "s420")})
    rows = aggregate_purchase(_result(), scope=scope)
    assert all(r.profile == "IPE200" and r.material == "S420" for r in rows)
    assert sum(r.count for r in rows) == 1


def test_aggregate_purchase_scope_none_returns_all():
    assert len(aggregate_purchase(_result(), scope=None)) == 4


def test_aggregate_purchase_empty_scope_returns_empty():
    assert aggregate_purchase(_result(), scope=frozenset()) == []


def test_aggregate_prep_groups_lengths_with_totals():
    preps = aggregate_prep(_result())
    by_section = {(p.profile, p.material): p for p in preps}
    s = by_section[("IPE200", "S275JR")]
    assert s.by_length == [(12000.0, 2), (6000.0, 1)]
    assert s.total_bars == 3
    assert s.linear_m == pytest.approx(30.0)


def test_aggregate_prep_respects_scope():
    scope = frozenset({("hea300", "s275jr")})
    preps = aggregate_prep(_result(), scope=scope)
    assert len(preps) == 1
    assert preps[0].profile == "HEA300"
    assert preps[0].total_bars == 2


def test_available_scope_keys_is_stable_and_distinct():
    keys = available_scope_keys(_result())
    assert keys == [
        ("IPE200", "S275JR"),
        ("IPE200", "S420"),
        ("HEA300", "S275JR"),
    ]


def test_filter_profiles_none_returns_full_list():
    assert len(filter_profiles(_result(), None)) == 3


def test_filter_profiles_is_case_insensitive():
    scope = frozenset({("IPE200".lower(), "s275JR".lower())})
    assert len(filter_profiles(_result(), scope)) == 1


def test_grand_totals_sums_count_and_linear_m():
    rows = aggregate_purchase(_result())
    count, lm = grand_totals(rows)
    # 2*12 + 1*6 + 1*12 + 2*6 = 24 + 6 + 12 + 12 = 54 m, 6 bars
    assert count == 6
    assert lm == pytest.approx(54.0)

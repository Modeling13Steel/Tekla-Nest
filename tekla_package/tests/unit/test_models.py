"""Unit tests for all model dataclasses."""

from __future__ import annotations

import pytest
from tekla_nest.models import (
    BarResult,
    CutPiece,
    NestResult,
    PartEntry,
    ProfileResult,
    StockBar,
    StockEntry,
)

# ── CutPiece ─────────────────────────────────────────────────


class TestCutPiece:
    def test_create(self):
        cp = CutPiece(length=3000.0, mark="A1")
        assert cp.length == 3000.0
        assert cp.mark == "A1"

    def test_equality(self):
        a = CutPiece(length=3000.0, mark="A1")
        b = CutPiece(length=3000.0, mark="A1")
        assert a == b

    def test_inequality(self):
        a = CutPiece(length=3000.0, mark="A1")
        b = CutPiece(length=4000.0, mark="A1")
        assert a != b


# ── PartEntry ────────────────────────────────────────────────


class TestPartEntry:
    def test_create(self):
        pe = PartEntry(
            quantity=5, length=2500.0, reference="C3", profile="HEA240", material="S275JR"
        )
        assert pe.quantity == 5
        assert pe.length == 2500.0
        assert pe.reference == "C3"
        assert pe.profile == "HEA240"
        assert pe.material == "S275JR"

    def test_equality(self):
        a = PartEntry(1, 1000.0, "X", "IPE200", "S355")
        b = PartEntry(1, 1000.0, "X", "IPE200", "S355")
        assert a == b


# ── StockBar ─────────────────────────────────────────────────


class TestStockBar:
    def test_create(self):
        sb = StockBar(length=12000.0, mark="HEA240", material="S275JR", source="Mercado")
        assert sb.length == 12000.0
        assert sb.source == "Mercado"

    def test_client_source(self):
        sb = StockBar(length=6100.0, mark="IPE200", material="S355", source="Cliente")
        assert sb.source == "Cliente"


# ── StockEntry ───────────────────────────────────────────────


class TestStockEntry:
    def test_create_with_defaults(self):
        se = StockEntry(quantity=10, length=6000.0, priority=0, profile="HEA240", material="S275")
        assert se.source == "Mercado"  # default

    def test_create_with_explicit_source(self):
        se = StockEntry(
            quantity=5,
            length=10100.0,
            priority=-1000,
            profile="IPE200",
            material="S355",
            source="Cliente",
        )
        assert se.source == "Cliente"
        assert se.priority == -1000


# ── BarResult ────────────────────────────────────────────────


class TestBarResult:
    def test_empty_bar(self):
        br = BarResult(original_length=12000.0, mark="HEA240", material="S275", source="Mercado")
        assert br.cuts == []
        assert br.cut_marks == []
        assert br.free_length == 12000.0
        assert br.used_length == 0.0

    def test_with_cuts(self):
        br = BarResult(
            original_length=12000.0,
            mark="HEA240",
            material="S275",
            source="Mercado",
            cuts=[3000.0, 4000.0, 2000.0],
            cut_marks=["A1", "B1", "C1"],
        )
        assert br.used_length == pytest.approx(9000.0)
        assert br.free_length == pytest.approx(3000.0)

    def test_perfect_fit(self):
        br = BarResult(
            original_length=6000.0,
            mark="X",
            material="S275",
            source="Mercado",
            cuts=[6000.0],
            cut_marks=["A1"],
        )
        assert br.free_length == pytest.approx(0.0)
        assert br.used_length == pytest.approx(6000.0)

    def test_free_length_is_computed(self):
        br = BarResult(original_length=10000.0, mark="X", material="S", source="M")
        br.cuts.append(2500.0)
        br.cuts.append(3500.0)
        assert br.free_length == pytest.approx(4000.0)


# ── ProfileResult ────────────────────────────────────────────


class TestProfileResult:
    def test_empty_profile(self):
        pr = ProfileResult(profile="HEA240")
        assert pr.bars == []
        assert pr.waste_pct == 0.0
        assert pr.total_stock_length == 0.0
        assert pr.total_waste == 0.0
        assert pr.utilization_pct == 100.0

    def test_with_bars(self):
        b1 = BarResult(12000.0, "HEA", "S275", "Mercado", [3000.0, 4000.0], ["A", "B"])
        b2 = BarResult(6000.0, "HEA", "S275", "Mercado", [5000.0], ["C"])
        pr = ProfileResult(profile="HEA240", bars=[b1, b2], waste_pct=33.33)

        assert pr.total_stock_length == pytest.approx(18000.0)
        assert pr.total_waste == pytest.approx(6000.0)  # 5000 + 1000
        assert pr.utilization_pct == pytest.approx(66.67)

    def test_scrap_pct(self):
        pr = ProfileResult(profile="X", scrap_pct=2.5)
        assert pr.scrap_pct == 2.5


# ── NestResult ───────────────────────────────────────────────


class TestNestResult:
    def test_empty(self):
        nr = NestResult()
        assert nr.profiles == []
        assert nr.overall_waste_pct == 0.0

    def test_single_profile(self):
        br = BarResult(10000.0, "HEA", "S275", "M", [8000.0], ["A"])
        pr = ProfileResult("HEA240", [br], waste_pct=20.0)
        nr = NestResult(profiles=[pr])
        assert nr.overall_waste_pct == pytest.approx(20.0)

    def test_multiple_profiles(self):
        b1 = BarResult(10000.0, "HEA", "S275", "M", [9000.0], ["A"])  # 1000 waste
        b2 = BarResult(6000.0, "IPE", "S275", "M", [3000.0], ["B"])  # 3000 waste
        p1 = ProfileResult("HEA240", [b1])
        p2 = ProfileResult("IPE200", [b2])
        nr = NestResult(profiles=[p1, p2])

        # Total stock = 16000, total waste = 4000 → 25%
        assert nr.overall_waste_pct == pytest.approx(25.0)

    def test_zero_stock_gives_zero_waste(self):
        pr = ProfileResult("X", bars=[])
        nr = NestResult(profiles=[pr])
        assert nr.overall_waste_pct == 0.0

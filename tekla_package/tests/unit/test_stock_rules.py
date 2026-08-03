"""Unit tests for stock_rules service."""

from __future__ import annotations

import pytest
from tekla_common.config.app_config import load_config, reset_config
from tekla_nest.services.stock_rules import generate_default_stock


@pytest.fixture(autouse=True)
def _reset_cfg():
    """Reset config singleton before each test."""
    reset_config()
    load_config()
    yield
    reset_config()


class TestGenerateDefaultStock:
    def test_hot_rolled_profile_gets_6_lengths(self):
        # pairs API: (profile, material) — one material → 6 lengths
        entries = generate_default_stock([("HEA240", "S355JR")])
        assert len(entries) == 6
        assert sorted({e.length for e in entries}) == [
            6100.0,
            10100.0,
            12100.0,
            14100.0,
            15100.0,
            16100.0,
        ]

    def test_other_profile_gets_2_lengths(self):
        entries = generate_default_stock([("WI300-15-20*300", "S235JR")])
        assert len(entries) == 2

    def test_multiple_pairs(self):
        entries = generate_default_stock(
            [
                ("HEA240", "S355JR"),
                ("WI300", "S235JR"),
            ]
        )
        hea = [e for e in entries if e.profile == "HEA240"]
        wi = [e for e in entries if e.profile == "WI300"]
        assert len(hea) == 6  # 6 lengths
        assert len(wi) == 2  # 2 lengths

    def test_all_entries_are_mercado(self):
        entries = generate_default_stock([("IPE200", "S355JR")])
        for e in entries:
            assert e.source == "Mercado"

    def test_all_entries_have_priority_zero(self):
        entries = generate_default_stock([("HEB300", "S235JR")])
        for e in entries:
            assert e.priority == 0

    def test_default_quantity_from_config(self):
        entries = generate_default_stock([("HEA240", "S235JR")])
        for e in entries:
            assert e.quantity == 100

    def test_empty_pairs_list(self):
        entries = generate_default_stock([])
        assert entries == []

    def test_blank_profile_skipped(self):
        entries = generate_default_stock([("", "S235JR"), ("  ", "S235JR"), ("HEA240", "S355JR")])
        assert len(entries) == 6  # only HEA240 × 6 lengths

    @pytest.mark.parametrize("family", ["HEB", "HEA", "HEM", "IPE", "IPN", "UPN", "UPE"])
    def test_all_hot_rolled_families(self, family):
        entries = generate_default_stock([(f"{family}200", "S235JR")])
        assert len(entries) == 6, f"{family} should produce 6 lengths"

    def test_hot_rolled_lengths_values(self):
        entries = generate_default_stock([("HEA240", "S235JR")])
        lengths = sorted({e.length for e in entries})
        assert lengths == [6100.0, 10100.0, 12100.0, 14100.0, 15100.0, 16100.0]

    def test_other_lengths_values(self):
        entries = generate_default_stock([("CUSTOM_PROFILE", "S235JR")])
        lengths = sorted({e.length for e in entries})
        assert lengths == [6000.0, 12000.0]

    def test_material_preserved_per_pair(self):
        entries = generate_default_stock(
            [
                ("HEA240", "S235JR"),
                ("HEA240", "S275JR"),
                ("HEA240", "S355JR"),
            ]
        )
        materials = sorted({e.material for e in entries})
        assert materials == ["S235JR", "S275JR", "S355JR"]
        # Each (length, material) pair appears exactly once
        pairs = [(e.length, e.material) for e in entries]
        assert len(pairs) == len(set(pairs))

    def test_profile_name_preserved(self):
        entries = generate_default_stock([("HEA 240", "S235JR")])
        for e in entries:
            assert e.profile == "HEA 240"

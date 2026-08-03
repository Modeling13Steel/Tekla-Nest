"""ms-007: Tests for auto-stock duplicate fix and material scoping.

TEST-001 — auto_populate_stock replace semantics
TEST-002 — auto_populate_stock material scoping
TEST-003 — generate_default_stock pairs API
TEST-004 — over-length bar seeding preserved
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from tekla_nest.models import PartEntry
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.services.stock_rules import generate_default_stock

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_config():
    """Return a simple config-like object covering the fields used by stock logic."""
    return SimpleNamespace(
        materials=["S235JR", "S275JR", "S355JR"],
        hot_rolled_families=["HEB", "IPE"],
        hot_rolled_lengths=[6100, 12100],
        other_lengths=[6000, 12000],
        default_stock_quantity=10,
        kerf_width=0.0,
        scrap_threshold=2000.0,
        max_strategies=6,
    )


def _make_part(profile: str, material: str, length: float = 3000.0) -> PartEntry:
    return PartEntry(
        quantity=1,
        length=length,
        reference="TEST",
        profile=profile,
        material=material,
    )


# ---------------------------------------------------------------------------
# TEST-001: replace semantics — calling auto_populate_stock twice must not
#           double the market stock entries.
# ---------------------------------------------------------------------------


class TestReplaceSemantics:
    """TEST-001"""

    def test_replace_semantics(self, qtbot):
        """market_stock_replaced emitted twice with identical content each time."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [
                _make_part("HEB200", "S355JR"),
                _make_part("IPE300", "S355JR"),
            ]

            emissions: list[list] = []
            presenter.market_stock_replaced.connect(lambda entries: emissions.append(list(entries)))

            presenter.auto_populate_stock()
            presenter.auto_populate_stock()

        assert len(emissions) == 2, "market_stock_replaced should fire on each call"
        # The second call must produce the same count — not doubled
        assert len(emissions[0]) == len(emissions[1]), (
            f"Second call doubled entries: {len(emissions[0])} → {len(emissions[1])}"
        )

    def test_stock_loaded_not_emitted_by_auto_populate(self, qtbot):
        """auto_populate_stock must NOT emit stock_loaded (would cause appending)."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [_make_part("HEB200", "S355JR")]

            stock_loaded_calls: list = []
            presenter.stock_loaded.connect(lambda e: stock_loaded_calls.append(e))

            presenter.auto_populate_stock()

        assert stock_loaded_calls == [], "stock_loaded must not be emitted by auto_populate_stock"


# ---------------------------------------------------------------------------
# TEST-002: material scoping — only materials present in parts are seeded.
# ---------------------------------------------------------------------------


class TestMaterialScoping:
    """TEST-002"""

    def test_material_scoping(self, qtbot):
        """Parts all use S355JR — no S235JR or S275JR entries should appear."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [
                _make_part("HEB200", "S355JR"),
                _make_part("IPE300", "S355JR"),
            ]

            emitted: list[list] = []
            presenter.market_stock_replaced.connect(lambda e: emitted.append(list(e)))

            presenter.auto_populate_stock()

        assert emitted, "market_stock_replaced must be emitted"
        entries = emitted[0]
        materials = {e.material for e in entries}
        assert materials == {"S355JR"}, f"Expected only S355JR; got {materials}"
        assert "S235JR" not in materials
        assert "S275JR" not in materials

    def test_mixed_materials_only_present_ones(self, qtbot):
        """Parts use S275JR and S355JR — only those two materials should appear."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [
                _make_part("HEB200", "S275JR"),
                _make_part("IPE300", "S355JR"),
            ]

            emitted: list[list] = []
            presenter.market_stock_replaced.connect(lambda e: emitted.append(list(e)))
            presenter.auto_populate_stock()

        assert emitted
        materials = {e.material for e in emitted[0]}
        assert materials == {"S275JR", "S355JR"}
        assert "S235JR" not in materials


# ---------------------------------------------------------------------------
# TEST-003: generate_default_stock pairs API
# ---------------------------------------------------------------------------


class TestGeneratePairs:
    """TEST-003"""

    def test_generate_pairs(self):
        """generate_default_stock([("HEB200", "S355JR"), ("IPE300", "S275JR")]) should
        produce entries for both pairs and no S235JR entries."""
        with patch(
            "tekla_nest.services.stock_rules.get_config",
            return_value=_make_config(),
        ):
            entries = generate_default_stock(
                [
                    ("HEB200", "S355JR"),
                    ("IPE300", "S275JR"),
                ]
            )

        heb_s355 = [e for e in entries if e.profile == "HEB200" and e.material == "S355JR"]
        ipe_s275 = [e for e in entries if e.profile == "IPE300" and e.material == "S275JR"]
        no_s235 = [e for e in entries if e.material == "S235JR"]

        assert len(heb_s355) >= 1, "Must have at least one HEB200/S355JR entry"
        assert len(ipe_s275) >= 1, "Must have at least one IPE300/S275JR entry"
        assert no_s235 == [], f"Should have no S235JR entries, got: {no_s235}"

    def test_each_pair_gets_independent_lengths(self):
        """Each (profile, material) pair gets its own set of lengths."""
        with patch(
            "tekla_nest.services.stock_rules.get_config",
            return_value=_make_config(),
        ):
            entries = generate_default_stock(
                [
                    ("HEB200", "S355JR"),
                    ("HEB200", "S275JR"),
                ]
            )

        heb_s355 = [e for e in entries if e.material == "S355JR"]
        heb_s275 = [e for e in entries if e.material == "S275JR"]
        # Both should have the same lengths (hot rolled → 2 lengths in mock config)
        assert len(heb_s355) == 2
        assert len(heb_s275) == 2


# ---------------------------------------------------------------------------
# TEST-004: over-length bar seeding preserved
# ---------------------------------------------------------------------------


class TestOverlengthSeeding:
    """TEST-004"""

    def test_overlength_seeding(self, qtbot):
        """A part with length 17000mm (> 12100mm max standard) must produce
        a stock bar with length >= 17000."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [
                _make_part("HEB200", "S355JR", length=17000.0),
            ]

            emitted: list[list] = []
            presenter.market_stock_replaced.connect(lambda e: emitted.append(list(e)))
            presenter.auto_populate_stock()

        assert emitted
        lengths = [e.length for e in emitted[0]]
        assert any(ln >= 17000.0 for ln in lengths), (
            f"Expected a bar >= 17000mm for the over-length piece; got lengths={sorted(lengths)}"
        )

    def test_no_overlength_bar_when_standard_covers_piece(self, qtbot):
        """A 3000mm part (well within 12100mm standard) must not trigger an
        extra bar — the standard lengths are sufficient."""
        with (
            patch(
                "tekla_nest.presenters.nest_presenter.get_config",
                return_value=_make_config(),
            ),
            patch(
                "tekla_nest.services.stock_rules.get_config",
                return_value=_make_config(),
            ),
        ):
            presenter = NestPresenter()
            presenter._parts = [
                _make_part("HEB200", "S355JR", length=3000.0),
            ]

            emitted: list[list] = []
            presenter.market_stock_replaced.connect(lambda e: emitted.append(list(e)))
            presenter.auto_populate_stock()

        assert emitted
        # Standard hot-rolled lengths in mock config are 6100 and 12100
        # No extra bar above 12100 should appear
        extra_bars = [e for e in emitted[0] if e.length > 12100.0]
        assert extra_bars == [], f"Unexpected over-length bars for a 3000mm piece: {extra_bars}"

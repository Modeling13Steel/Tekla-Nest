"""F14 — auto-stock must cover every (profile, material) in the parts.

The previous behaviour seeded stock only for materials in
``cfg.materials`` (default S235JR/S275JR/S355JR). Any part declaring
a material outside that list (custom grade, regional steel, blank,
typo) produced "No stock available for this profile" on the report
even after clicking Auto-stock. This pins the harder contract: every
(profile, material) seen in the parts list MUST have matching stock
after Auto-stock runs.
"""

from __future__ import annotations

import pytest
from tekla_nest.models import PartEntry


@pytest.mark.parametrize(
    "material",
    [
        "S420",  # grade not in cfg.materials default
        "Q235",  # Asian grade
        "S275-JR",  # punctuation variant
        "",  # blank
        "AlMgSi",  # aluminum
        "  S275JR  ",  # whitespace
    ],
)
def test_auto_stock_covers_unconfigured_material(presenter, material):
    presenter.set_parts(
        [
            PartEntry(quantity=2, length=3000, reference="P1", profile="IPE200", material=material),
        ]
    )
    presenter.auto_populate_stock()
    presenter.run_optimization()
    result = presenter._last_result
    assert result is not None
    assert len(result.profiles) == 1
    pr = result.profiles[0]
    # The actual fix: we should have at least one bar — never "no stock"
    assert len(pr.bars) >= 1, (
        f"material {material!r}: no stock seeded — report would say "
        f"'no stock available for this profile'"
    )
    assert pr.unfit_pieces == []


def test_auto_stock_covers_mixed_materials_same_profile(presenter):
    presenter.set_parts(
        [
            PartEntry(quantity=2, length=3000, reference="P1", profile="IPE200", material="S275JR"),
            PartEntry(quantity=1, length=4500, reference="P2", profile="IPE200", material="S420"),
        ]
    )
    presenter.auto_populate_stock()
    presenter.run_optimization()
    profiles = presenter._last_result.profiles
    by_material = {p.material: p for p in profiles}
    assert "S275JR" in by_material
    assert "S420" in by_material
    assert len(by_material["S275JR"].bars) >= 1
    assert len(by_material["S420"].bars) >= 1


def test_auto_stock_covers_custom_profile_and_material(presenter):
    presenter.set_parts(
        [
            PartEntry(
                quantity=2, length=3000, reference="P1", profile="L60x60x6", material="AlMgSi"
            ),
        ]
    )
    presenter.auto_populate_stock()
    presenter.run_optimization()
    pr = presenter._last_result.profiles[0]
    assert pr.profile == "L60x60x6"
    assert pr.material == "AlMgSi"
    assert len(pr.bars) >= 1


def test_auto_stock_covers_over_length_pieces(presenter):
    """Piece longer than the default 12m bar must still be cuttable.

    User repro: WI300-15-20*300 / STEEL_UNDEFINED / 18000 mm × 1.
    Auto-stock reported '100 × 6 m + 100 × 12 m' but the optimizer
    rejected the 18 m piece as 'not enough stock'. Auto-stock now
    seeds an extra bar long enough for the longest piece in each
    (profile, material) combo.
    """
    presenter.set_parts(
        [
            PartEntry(
                quantity=1,
                length=18000,
                reference="P1",
                profile="WI300-15-20*300",
                material="STEEL_UNDEFINED",
            ),
        ]
    )
    presenter.auto_populate_stock()
    presenter.run_optimization()
    result = presenter._last_result
    assert result is not None and result.profiles
    pr = result.profiles[0]
    assert pr.unfit_pieces == [], f"18m piece left unfit: {pr.unfit_pieces}"
    assert any(b.original_length >= 18000 for b in pr.bars), (
        f"no bar >= 18m in plan: {[b.original_length for b in pr.bars]}"
    )


def test_auto_stock_rounds_up_over_length_to_next_500(presenter):
    presenter.set_parts(
        [
            PartEntry(
                quantity=1,
                length=13250,
                reference="P1",
                profile="WI300-15-20*300",
                material="STEEL_UNDEFINED",
            ),
        ]
    )
    presenter.auto_populate_stock()
    bars_for = [
        s
        for s in presenter._market_stock
        if s.profile == "WI300-15-20*300" and s.material == "STEEL_UNDEFINED"
    ]
    assert any(s.length == 13500 for s in bars_for), (
        f"expected a 13500mm bar; got {[s.length for s in bars_for]}"
    )

"""Generate default market stock entries for known profile families.

Migrated from: C# FrmNest.aTRIBUIRSTOKAUTOMATICOToolStripMenuItem_Click
Config-driven: lengths and families come from config.yaml.
"""

from __future__ import annotations

from tekla_common.config.app_config import get_config

from ..models import StockEntry


def generate_default_stock(pairs: list[tuple[str, str]]) -> list[StockEntry]:
    """Generate default market stock entries for a list of (profile, material) pairs.

    Hot-rolled families (HEB, IPE, etc.) get extended length options.
    Other profiles get basic lengths.

    Only the exact (profile, material) combinations present in the parts
    are seeded, so no spurious entries are created for materials that are
    not actually used.

    Args:
        pairs: Distinct (profile, material) tuples from the parts table.

    Returns:
        List of StockEntry with source="Mercado" and priority=0.
    """
    cfg = get_config()
    entries: list[StockEntry] = []

    for profile, material in pairs:
        if not profile or not profile.strip():
            continue

        profile_upper = profile.strip().upper()
        is_hot_rolled = any(
            profile_upper.startswith(fam) or fam in profile_upper for fam in cfg.hot_rolled_families
        )

        lengths = cfg.hot_rolled_lengths if is_hot_rolled else cfg.other_lengths

        for length in lengths:
            entries.append(
                StockEntry(
                    quantity=cfg.default_stock_quantity,
                    length=length,
                    priority=0,
                    profile=profile,
                    material=material,
                    source="Mercado",
                )
            )

    return entries

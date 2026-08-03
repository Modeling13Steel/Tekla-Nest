"""M2: EN and PT catalogues must define the same set of translation keys.

Closes risk R-06 from REFACTOR_PLAN: drift between language files leads to
silent fallbacks in production. This test asserts strict parity.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest
from tekla_common.i18n import _catalog


def _flat_keys(node: object, prefix: str = "") -> Iterable[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            child = f"{prefix}.{k}" if prefix else k
            yield from _flat_keys(v, child)
    else:
        yield prefix


def test_en_and_pt_have_identical_key_sets() -> None:
    en_keys = set(_flat_keys(_catalog("en")))
    pt_keys = set(_flat_keys(_catalog("pt")))
    missing_in_pt = en_keys - pt_keys
    extra_in_pt = pt_keys - en_keys
    assert not missing_in_pt, f"keys missing from pt.yaml: {sorted(missing_in_pt)}"
    assert not extra_in_pt, f"keys extra in pt.yaml: {sorted(extra_in_pt)}"


@pytest.mark.parametrize(
    "key",
    [
        "chrome.theme_toggle.light",
        "chrome.theme_toggle.dark",
        "chrome.theme_toggle.system",
        "chrome.command_palette.tooltip",
        "chrome.language.tooltip",
        "kpi.placeholder",
        "kpi.waste_pct",
        "kpi.bars_used",
        "kpi.unfit_count",
        "kpi.profile_count",
        "statusbar.accessible_name",
    ],
)
def test_m2_keys_present_in_both_catalogs(key: str) -> None:
    en_keys = set(_flat_keys(_catalog("en")))
    pt_keys = set(_flat_keys(_catalog("pt")))
    assert key in en_keys, f"{key} missing in en.yaml"
    assert key in pt_keys, f"{key} missing in pt.yaml"

"""M7 — WCAG AA contrast guard for the dark-theme palette."""

from __future__ import annotations

import pytest
from tekla_common.design_system.tokens import contrast_ratio, dark_color_tokens

_AA_NORMAL_TEXT = 4.5
_AA_LARGE_TEXT = 3.0

# Pairs that must hit the *text* threshold (4.5:1).
_TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("text_primary", "bg_app"),
    ("text_primary", "bg_surface"),
    ("text_primary", "bg_subtle"),
    ("text_muted", "bg_app"),
    ("text_muted", "bg_surface"),
    ("text_secondary", "bg_surface"),
)

# Pairs that may use the relaxed "large text / UI element" threshold (3:1).
_UI_PAIRS: tuple[tuple[str, str], ...] = (
    ("action_primary", "bg_surface"),
    ("action_accent", "bg_surface"),
    ("state_success", "bg_surface"),
    ("state_warning", "bg_surface"),
    ("state_danger", "bg_surface"),
    ("state_info", "bg_surface"),
    ("focus_ring", "bg_surface"),
)


def _hex(value: str) -> str:
    """Strip any 'rgba(...)' wrappers to a pure hex string for ratio calc.

    Dark tokens are all hex; if a token ever becomes rgba it would short-
    circuit luminance calculation. We only validate hex tokens here.
    """
    if value.startswith("rgba") or value.startswith("rgb("):
        pytest.skip(f"non-hex token {value}")
    return value


@pytest.mark.parametrize("fg_key,bg_key", _TEXT_PAIRS)
def test_dark_text_pairs_meet_aa(fg_key, bg_key):
    tokens = dark_color_tokens()
    ratio = contrast_ratio(_hex(getattr(tokens, fg_key)), _hex(getattr(tokens, bg_key)))
    assert ratio >= _AA_NORMAL_TEXT, f"{fg_key} on {bg_key}: {ratio:.2f} < 4.5"


@pytest.mark.parametrize("fg_key,bg_key", _UI_PAIRS)
def test_dark_ui_pairs_meet_aa_large(fg_key, bg_key):
    tokens = dark_color_tokens()
    ratio = contrast_ratio(_hex(getattr(tokens, fg_key)), _hex(getattr(tokens, bg_key)))
    assert ratio >= _AA_LARGE_TEXT, f"{fg_key} on {bg_key}: {ratio:.2f} < 3.0"

"""M1: dark palette validation — hex shape + WCAG AA contrast."""
from __future__ import annotations

import re

from tekla_nest.config.app_config import AppConfig
from tekla_nest.design_system.tokens import (
    Theme,
    build_design_tokens_for_theme,
    contrast_ratio,
    dark_color_tokens,
)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_dark_tokens_core_fields_are_hex() -> None:
    dark = dark_color_tokens()
    for field_name in (
        "bg_app",
        "bg_surface",
        "bg_subtle",
        "text_primary",
        "text_muted",
        "border_default",
        "action_primary",
        "action_accent",
        "state_success",
        "state_warning",
        "state_danger",
        "state_info",
        "focus_ring",
        "disabled_fg",
    ):
        value = getattr(dark, field_name)
        assert _HEX_RE.match(value), f"{field_name}={value!r} is not a #RRGGBB hex"


def test_dark_tokens_meet_wcag_aa_for_body_text() -> None:
    dark = dark_color_tokens()
    # AA body text needs ≥ 4.5:1
    assert contrast_ratio(dark.text_primary, dark.bg_app) >= 4.5
    assert contrast_ratio(dark.text_primary, dark.bg_surface) >= 4.5


def test_build_tokens_for_dark_uses_dark_defaults() -> None:
    cfg = AppConfig()
    tokens = build_design_tokens_for_theme(cfg, Theme.DARK)
    dark = dark_color_tokens()
    assert tokens.colors.bg_app == dark.bg_app
    assert tokens.colors.text_primary == dark.text_primary


def test_build_tokens_for_dark_honours_brand_override() -> None:
    cfg = AppConfig(primary_color="#ff00aa", accent_color="#00ddee")
    tokens = build_design_tokens_for_theme(cfg, Theme.DARK)
    assert tokens.colors.action_primary == "#ff00aa"
    assert tokens.colors.action_accent == "#00ddee"
    assert tokens.colors.focus_ring == "#00ddee"


def test_build_tokens_for_light_ignores_cfg_background_dark_hack() -> None:
    # cfg.background dark must not flip the explicit-theme path
    cfg = AppConfig(background="#000000")
    light_tokens = build_design_tokens_for_theme(cfg, Theme.LIGHT)
    # Default light bg, not the cfg.background override
    assert light_tokens.colors.bg_app == "#f6f8fb"

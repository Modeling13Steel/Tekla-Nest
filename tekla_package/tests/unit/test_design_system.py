from __future__ import annotations

from tekla_common.config.app_config import AppConfig
from tekla_common.design_system.tokens import build_design_tokens, contrast_ratio
from tekla_common.theme import build_app_stylesheet


def test_default_tokens_use_spec_palette():
    cfg = AppConfig()

    tokens = build_design_tokens(cfg)

    assert tokens.colors.bg_app == "#f6f8fb"
    assert tokens.colors.action_primary == "#1d4ed8"
    assert tokens.colors.action_accent == "#0f766e"


def test_stylesheet_uses_semantic_selectors_and_not_legacy_palette():
    qss = build_app_stylesheet(AppConfig())

    assert "QFrame#statusBanner" in qss
    assert 'QTableView[tableState="error"]' in qss
    assert 'QPushButton[role="secondary"]' in qss
    assert "#1a73e8" not in qss
    assert "#ff6d00" not in qss
    assert "#f5f5f5" not in qss


def test_theme_config_overrides_primary_accent_and_background():
    cfg = AppConfig(
        primary_color="#ff0000",
        accent_color="#00ff00",
        background="#0000ff",
    )

    tokens = build_design_tokens(cfg)
    qss = build_app_stylesheet(cfg)

    assert tokens.colors.action_primary == "#ff0000"
    assert tokens.colors.action_accent == "#00ff00"
    assert tokens.colors.bg_app == "#0000ff"
    assert "#ff0000" in qss
    assert "#00ff00" in qss
    assert "#0000ff" in qss


def test_dark_background_tokens_keep_text_contrast():
    tokens = build_design_tokens(AppConfig(background="#172033"))

    assert tokens.colors.bg_surface == "#111827"
    assert contrast_ratio(tokens.colors.text_primary, tokens.colors.bg_app) >= 4.5
    assert contrast_ratio(tokens.colors.border_default, tokens.colors.bg_app) >= 3.0

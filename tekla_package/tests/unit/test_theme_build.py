"""M1: theme stylesheet builders — coverage of selectors + back-compat."""

from __future__ import annotations

from tekla_common.config.app_config import AppConfig
from tekla_common.design_system.tokens import Theme
from tekla_common.theme import (
    build_all_stylesheets,
    build_app_stylesheet,
    build_themed_stylesheet,
)


def test_legacy_light_matches_new_themed_light_byte_for_byte() -> None:
    """Critical back-compat guarantee: M1 must not change the v2.0 light QSS."""
    cfg = AppConfig()
    assert build_app_stylesheet(cfg) == build_themed_stylesheet(cfg, Theme.LIGHT)


def test_build_all_stylesheets_returns_both_themes() -> None:
    cfg = AppConfig()
    sheets = build_all_stylesheets(cfg)
    assert set(sheets.keys()) == {Theme.LIGHT, Theme.DARK}
    assert sheets[Theme.LIGHT] != sheets[Theme.DARK]


def test_stylesheet_contains_expected_selectors() -> None:
    cfg = AppConfig()
    for theme in (Theme.LIGHT, Theme.DARK):
        sheet = build_themed_stylesheet(cfg, theme)
        for selector in (
            "QMainWindow",
            "QPushButton",
            "appShell",
            "brandToolbar",
            "QHeaderView::section",
            "QTabBar::tab",
            "QToolTip",
        ):
            assert selector in sheet, f"missing {selector} in {theme} sheet"


def test_dark_stylesheet_uses_dark_bg() -> None:
    cfg = AppConfig()
    dark = build_themed_stylesheet(cfg, Theme.DARK)
    assert "#0b1220" in dark  # dark bg_app


def test_brand_override_appears_in_sheet() -> None:
    cfg = AppConfig(primary_color="#ff00aa")
    sheet = build_themed_stylesheet(cfg, Theme.LIGHT)
    assert "#ff00aa" in sheet

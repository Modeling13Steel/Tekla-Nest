"""F7 — Theme, language, reduced motion preferences."""

from __future__ import annotations

import pytest
from tekla_common.config.app_config import get_config
from tekla_common.design_system.tokens import Theme
from tekla_common.i18n import current_language, set_language, tr
from tekla_nest.services.theme_service import ThemeService


@pytest.fixture
def theme_service(qtbot):
    return ThemeService(get_config())


class TestThemeSwitching:
    def test_light_to_dark_emits_signal(self, theme_service, qtbot):
        theme_service.apply(Theme.LIGHT)
        with qtbot.waitSignal(theme_service.themeChanged, timeout=1000):
            theme_service.apply(Theme.DARK)
        assert theme_service.resolved() == Theme.DARK

    def test_dark_to_light_round_trip(self, theme_service):
        theme_service.apply(Theme.DARK)
        assert theme_service.resolved() == Theme.DARK
        theme_service.apply(Theme.LIGHT)
        assert theme_service.resolved() == Theme.LIGHT

    def test_stylesheet_differs_between_themes(self, theme_service):
        theme_service.apply(Theme.LIGHT)
        light = theme_service.stylesheet()
        theme_service.apply(Theme.DARK)
        dark = theme_service.stylesheet()
        assert light != dark


class TestLanguageSwitch:
    def test_pt_translates_known_key(self):
        set_language("en")
        en = tr("commands.calculate.text")
        set_language("pt")
        pt = tr("commands.calculate.text")
        assert en != pt, f"PT translation missing: en={en!r} pt={pt!r}"
        # Sanity: both should resolve, not return the raw key
        assert "." not in en and "." not in pt

    def test_round_trip(self):
        set_language("en")
        assert current_language() == "en"
        set_language("pt")
        assert current_language() == "pt"
        set_language("en")
        assert current_language() == "en"

    def test_unknown_key_returns_fallback(self):
        result = tr("__definitely_missing__.__key__")
        assert isinstance(result, str)


class TestReducedMotion:
    def test_persists_to_config(self, journey):
        journey.window._apply_reduced_motion(True)
        assert get_config().prefer_reduced_motion is True
        journey.window._apply_reduced_motion(False)
        assert get_config().prefer_reduced_motion is False

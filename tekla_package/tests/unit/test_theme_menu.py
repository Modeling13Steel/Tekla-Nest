"""M7 — Preferences→Theme menu drives ThemeService and persists choice."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tekla_common.config.app_config import load_config
from tekla_common.design_system.tokens import Theme
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.services.theme_service import ThemeService
from tekla_nest.views.nest_window import NestWindow


@pytest.fixture
def prefs_path(tmp_path: Path) -> Path:
    return tmp_path / "preferences.json"


def _make_service(prefs_path: Path) -> ThemeService:
    cfg = load_config()
    return ThemeService(cfg, prefs_path=prefs_path)


def test_theme_menu_has_system_light_dark(qtbot, prefs_path):
    service = _make_service(prefs_path)
    window = NestWindow(NestPresenter(), theme_service=service)
    qtbot.addWidget(window)
    assert set(window._theme_actions) == {Theme.SYSTEM, Theme.LIGHT, Theme.DARK}


def test_triggering_dark_menu_action_applies_dark_theme(qtbot, prefs_path):
    service = _make_service(prefs_path)
    window = NestWindow(NestPresenter(), theme_service=service)
    qtbot.addWidget(window)
    window._theme_actions[Theme.DARK].trigger()
    assert service.current() is Theme.DARK
    assert window._theme_actions[Theme.DARK].isChecked()


def test_theme_choice_persists_across_restart(qtbot, prefs_path):
    service = _make_service(prefs_path)
    window = NestWindow(NestPresenter(), theme_service=service)
    qtbot.addWidget(window)
    window._theme_actions[Theme.DARK].trigger()
    # Simulate restart: build a fresh service from the same prefs file.
    fresh = _make_service(prefs_path)
    assert fresh.current() is Theme.DARK
    assert json.loads(prefs_path.read_text("utf-8"))["theme"] == "dark"


def test_theme_menu_label_localised_pt(qtbot, prefs_path):
    from tekla_common.i18n import set_language

    service = _make_service(prefs_path)
    window = NestWindow(NestPresenter(), theme_service=service)
    qtbot.addWidget(window)
    set_language("pt")
    window._retranslate()
    assert window._theme_actions[Theme.DARK].text() == "Escuro"
    assert window._menus["preferences"].title() == "Preferências"
    set_language("en")
    window._retranslate()


def test_chrome_theme_toggle_signals_route_through_service(qtbot, prefs_path):
    service = _make_service(prefs_path)
    window = NestWindow(NestPresenter(), theme_service=service)
    qtbot.addWidget(window)
    window._chrome.theme_toggled.emit(Theme.LIGHT)
    assert service.current() is Theme.LIGHT

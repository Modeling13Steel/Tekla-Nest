"""M1: ThemeService — signals, persistence, SYSTEM resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tekla_common.config.app_config import AppConfig
from tekla_common.design_system.tokens import Theme
from tekla_nest.services.theme_service import ThemeService


@pytest.fixture
def prefs(tmp_path: Path) -> Path:
    return tmp_path / "preferences.json"


@pytest.fixture
def no_qapp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin SYSTEM resolution to LIGHT by hiding QGuiApplication.instance()."""
    monkeypatch.setattr(
        "tekla_nest.services.theme_service.QGuiApplication.instance",
        staticmethod(lambda: None),
    )


def test_default_is_light_when_no_prefs_file(prefs: Path) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    assert svc.current() == Theme.LIGHT


def test_apply_persists_to_disk(prefs: Path) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    svc.apply(Theme.DARK)
    data = json.loads(prefs.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"


def test_persisted_choice_is_reloaded(prefs: Path) -> None:
    prefs.write_text(json.dumps({"theme": "light"}), encoding="utf-8")
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    assert svc.current() == Theme.LIGHT


def test_invalid_persisted_value_falls_back_to_light(prefs: Path) -> None:
    prefs.write_text(json.dumps({"theme": "bogus"}), encoding="utf-8")
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    assert svc.current() == Theme.LIGHT


def test_apply_emits_themechanged_on_resolved_change(prefs: Path, no_qapp: None) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)  # starts LIGHT
    received: list[Theme] = []
    svc.themeChanged.connect(received.append)
    svc.apply(Theme.DARK)
    assert received == [Theme.DARK]


def test_apply_does_not_emit_when_resolved_unchanged(prefs: Path, no_qapp: None) -> None:
    # Default is LIGHT; applying LIGHT is a no-op.
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    received: list[Theme] = []
    svc.themeChanged.connect(received.append)
    svc.apply(Theme.LIGHT)
    assert received == []


def test_resolved_returns_concrete_theme(prefs: Path) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    svc.apply(Theme.LIGHT)
    assert svc.resolved() == Theme.LIGHT
    svc.apply(Theme.DARK)
    assert svc.resolved() == Theme.DARK


def test_system_resolves_to_light_when_no_qapplication(prefs: Path, no_qapp: None) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    svc.apply(Theme.SYSTEM)
    assert svc.current() == Theme.SYSTEM
    assert svc.resolved() == Theme.LIGHT


def test_stylesheet_returns_a_qss_string(prefs: Path) -> None:
    svc = ThemeService(AppConfig(), prefs_path=prefs)
    svc.apply(Theme.DARK)
    sheet = svc.stylesheet()
    assert "QPushButton" in sheet
    assert "#0b1220" in sheet

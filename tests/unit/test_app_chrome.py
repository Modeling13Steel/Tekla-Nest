"""M2: AppChrome — top-bar widget tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from tekla_nest.design_system.tokens import Theme
from tekla_nest.views.widgets.app_chrome import AppChrome


@pytest.fixture
def chrome(qtbot) -> AppChrome:
    widget = AppChrome(Path("nope.png"), "Tekla Nest", "#ffffff")
    qtbot.addWidget(widget)
    return widget


def test_chrome_starts_with_light_theme(chrome: AppChrome) -> None:
    assert chrome.current_theme() == Theme.LIGHT


def test_theme_toggle_cycles_through_three_states(chrome: AppChrome, qtbot) -> None:
    received: list[Theme] = []
    chrome.theme_toggled.connect(received.append)

    chrome._on_theme_clicked()  # LIGHT -> DARK
    chrome._on_theme_clicked()  # DARK -> SYSTEM
    chrome._on_theme_clicked()  # SYSTEM -> LIGHT

    assert received == [Theme.DARK, Theme.SYSTEM, Theme.LIGHT]


def test_set_theme_does_not_emit_signal(chrome: AppChrome) -> None:
    received: list[Theme] = []
    chrome.theme_toggled.connect(received.append)
    chrome.set_theme(Theme.DARK)
    assert received == []
    assert chrome.current_theme() == Theme.DARK


def test_set_languages_populates_combo(chrome: AppChrome) -> None:
    chrome.set_languages({"en": "English", "pt": "Português"}, "pt")
    assert chrome._language_combo.count() == 2
    assert chrome._language_combo.currentData() == "pt"


def test_language_change_emits_code(chrome: AppChrome) -> None:
    received: list[str] = []
    chrome.language_changed.connect(received.append)
    chrome.set_languages({"en": "English", "pt": "Português"}, "en")
    chrome._language_combo.setCurrentIndex(1)
    assert received == ["pt"]


def test_palette_button_emits_signal(chrome: AppChrome, qtbot) -> None:
    received: list[None] = []
    chrome.palette_requested.connect(lambda: received.append(None))
    chrome._palette_button.click()
    assert len(received) == 1


def test_add_action_attaches_to_chrome(chrome: AppChrome, qtbot) -> None:
    from PySide6.QtGui import QAction

    action = QAction("Calc", chrome)
    chrome.add_action(action)
    assert action in chrome.actions()

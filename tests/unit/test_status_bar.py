"""M2: AmbientStatusBar tests."""
from __future__ import annotations

import pytest

from tekla_nest.views.widgets.status_bar import AmbientStatusBar


@pytest.fixture
def bar(qtbot) -> AmbientStatusBar:
    widget = AmbientStatusBar()
    qtbot.addWidget(widget)
    return widget


def test_default_level_is_ready(bar: AmbientStatusBar) -> None:
    assert bar.level == "ready"


def test_set_status_updates_message(bar: AmbientStatusBar) -> None:
    bar.set_status("Loading parts…", "loading")
    assert bar.message == "Loading parts…"
    assert bar.level == "loading"
    assert str(bar._dot.property("state")) == "loading"


def test_invalid_level_falls_back_to_ready(bar: AmbientStatusBar) -> None:
    bar.set_status("Hi", "nonsense")
    assert bar.level == "ready"


@pytest.mark.parametrize("level", ["ready", "loading", "success", "warning", "error", "permission"])
def test_all_valid_levels_round_trip(bar: AmbientStatusBar, level: str) -> None:
    bar.set_status("x", level)
    assert bar.level == level
    assert str(bar._dot.property("state")) == level

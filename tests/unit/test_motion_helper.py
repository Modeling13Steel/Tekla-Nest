"""M8 — motion helper honours reduced-motion preference + 200 ms cap."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLabel

from tekla_nest.config.app_config import get_config, reset_config
from tekla_nest.design_system.motion import animate, animate_value, is_reduced_motion


@pytest.fixture(autouse=True)
def restore_config():
    """Ensure tests start from a known reduced-motion state."""
    reset_config()
    cfg = get_config()
    original = cfg.prefer_reduced_motion
    yield
    cfg.prefer_reduced_motion = original


def test_default_is_motion_enabled():
    assert is_reduced_motion() is False


def test_animate_returns_animation_when_motion_enabled(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    anim = animate(label, b"windowOpacity", duration_ms=120, start=0.0, end=1.0)
    assert anim is not None
    assert anim.duration() == 120


def test_animate_returns_none_and_applies_end_when_reduced(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    get_config().prefer_reduced_motion = True
    anim = animate(label, b"windowOpacity", duration_ms=120, start=0.0, end=0.42)
    assert anim is None
    assert label.windowOpacity() == pytest.approx(0.42, abs=1e-2)


def test_animate_rejects_duration_above_cap(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    with pytest.raises(ValueError):
        animate(label, b"windowOpacity", duration_ms=201, start=0.0, end=1.0)


def test_animate_rejects_non_positive_duration(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    with pytest.raises(ValueError):
        animate(label, b"windowOpacity", duration_ms=0, start=0.0, end=1.0)


def test_animate_value_invokes_callback(qtbot):
    received: list[float] = []
    parent = QObject()
    anim = animate_value(
        duration_ms=60, start=0.0, end=10.0,
        on_update=received.append, parent=parent,
    )
    assert anim is not None
    anim.start()
    qtbot.waitUntil(lambda: anim.state() == anim.State.Stopped, timeout=500)
    assert received, "no ticks fired"
    assert received[-1] == pytest.approx(10.0)


def test_animate_value_reduced_motion_skips_animation():
    received: list[float] = []
    get_config().prefer_reduced_motion = True
    anim = animate_value(
        duration_ms=60, start=0.0, end=7.5, on_update=received.append,
    )
    assert anim is None
    assert received == [7.5]

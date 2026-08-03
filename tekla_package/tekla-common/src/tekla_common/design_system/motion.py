"""Motion — animation helper that honours the reduced-motion preference.

A single ``animate()`` helper produces a configured ``QPropertyAnimation``
for callers, *unless* the user has opted out of motion. In that case the
helper sets the end value immediately and returns ``None``, so callers
can write::

    anim = animate(self, b"windowOpacity", duration_ms=120, start=0.0, end=1.0)
    if anim is not None:
        anim.start()

The reduced-motion preference lives on ``AppConfig.prefer_reduced_motion``
which is read at call time so toggling at runtime takes effect without
restart.

Per the v2.1 mock spec: every animation produced here is capped at
``200 ms`` — exceeding that raises a ``ValueError`` so we can't
accidentally ship a sluggish UI.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QVariantAnimation,
)

from ..config.app_config import get_config

_MAX_DURATION_MS = 200


def is_reduced_motion() -> bool:
    """Return True when the user has asked us to skip animations."""
    cfg = get_config()
    return bool(getattr(cfg, "prefer_reduced_motion", False))


def animate(
    target: QObject,
    prop: bytes | str,
    *,
    duration_ms: int,
    start: object,
    end: object,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation | None:
    """Build a ``QPropertyAnimation``, or apply ``end`` instantly when reduced.

    Args:
        target: the ``QObject`` whose Qt property is animated.
        prop: the property name (bytes preferred; str is auto-encoded).
        duration_ms: animation duration. Must be ``1 <= d <= 200``.
        start: starting value for the property.
        end: end value for the property.
        easing: Qt easing curve (default ``OutCubic``).

    Returns:
        The configured (but not yet started) ``QPropertyAnimation``,
        or ``None`` when reduced-motion is on (caller still gets the
        end-state applied synchronously).
    """
    if not 1 <= duration_ms <= _MAX_DURATION_MS:
        raise ValueError(f"animate(): duration_ms must be 1..{_MAX_DURATION_MS}, got {duration_ms}")

    if is_reduced_motion():
        _set_property_now(target, prop, end)
        return None

    name = prop if isinstance(prop, (bytes, bytearray)) else prop.encode("ascii")
    anim = QPropertyAnimation(target, QByteArray(name))
    anim.setDuration(duration_ms)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(easing)
    return anim


def _set_property_now(target: QObject, prop: bytes | str, value: object) -> None:
    name = prop.decode("ascii") if isinstance(prop, (bytes, bytearray)) else prop
    target.setProperty(name, value)


def animate_value(
    *,
    duration_ms: int,
    start: float,
    end: float,
    on_update,
    parent: QObject | None = None,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation | None:
    """Tween a numeric value, invoking ``on_update(current)`` on each step.

    Used for "count-up" KPI tiles. Honours reduced-motion by calling
    ``on_update(end)`` once and returning ``None``.
    """
    if not 1 <= duration_ms <= _MAX_DURATION_MS:
        raise ValueError(
            f"animate_value(): duration_ms must be 1..{_MAX_DURATION_MS}, got {duration_ms}"
        )
    if is_reduced_motion():
        on_update(end)
        return None
    anim = QVariantAnimation(parent)
    anim.setDuration(duration_ms)
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(lambda v: on_update(float(v)))
    return anim

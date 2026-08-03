"""Semantic design tokens derived from spec-0001 mockups and the M1 refactor.

Two layers of tokens live here:

1. **Legacy layer** — the original ``ColorTokens`` defaults and
   ``build_design_tokens(cfg)`` function. These auto-detect light/dark from
   ``cfg.background`` (a colour-customisation feature, not a real theme
   system). Kept untouched for back-compat with the admin window, PDF
   reports, and the colour-customisation dialog.

2. **M1 explicit-theme layer** — adds the ``Theme`` enum, dark-palette
   factory, motion tokens, extended radii, and ``build_design_tokens_for_theme``.
   This is the path the new ``ThemeService`` consumes. It ignores
   ``cfg.background`` and uses the mockup palette directly.

All field defaults are additive — existing callers compile unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import StrEnum

from ..config.app_config import AppConfig

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class Theme(StrEnum):
    """Explicit theme selector for the M1 theming layer.

    ``SYSTEM`` resolves to ``LIGHT`` or ``DARK`` at apply time via the
    OS colour scheme (Qt ≥ 6.5). Values are persisted to
    ``~/.tekla_nest/preferences.json`` by ``ThemeService``.
    """

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class ColorTokens:
    # ── Legacy fields (defaults unchanged; do not edit in M1) ─────────
    bg_app: str = "#f6f8fb"
    bg_surface: str = "#ffffff"
    bg_subtle: str = "#eef2f7"
    text_primary: str = "#172033"
    text_muted: str = "#5b677a"
    border_default: str = "#8a94a6"
    action_primary: str = "#1d4ed8"
    action_primary_dark: str = "#173b6c"
    action_accent: str = "#0f766e"
    action_accent_subtle: str = "#e6fffb"
    action_cyan: str = "#0891b2"
    editable_focus_bg: str = "#ecfeff"
    state_success: str = "#15803d"
    state_warning: str = "#b45309"
    state_danger: str = "#b91c1c"
    state_info: str = "#2563eb"
    focus_ring: str = "#0f766e"
    disabled_fg: str = "#6b7280"
    white: str = "#ffffff"
    # ── M1 additive fields (mockup palette; consumed in M2+) ──────────
    text_secondary: str = "#475569"
    text_inverse: str = "#f8fafc"
    bg_surface_2: str = "#f8fafc"
    bg_elevated: str = "#ffffff"
    border_soft: str = "#e2e8f0"
    border_strong: str = "#94a3b8"
    bg_glass: str = "rgba(255, 255, 255, 0.72)"
    bg_overlay: str = "rgba(15, 23, 42, 0.48)"
    shadow_low: str = "0 1px 2px rgba(15, 23, 42, 0.06)"
    shadow_medium: str = "0 4px 12px rgba(15, 23, 42, 0.08)"
    shadow_high: str = "0 12px 32px rgba(15, 23, 42, 0.12)"


def dark_color_tokens() -> ColorTokens:
    """Build the dark-theme palette from the mockups (``docs/ui-mocks/styles.css``).

    Returned tokens override every field; brand primary/accent are
    brightened to maintain AA contrast on dark surfaces.
    """
    return ColorTokens(
        # Surfaces
        bg_app="#0b1220",
        bg_surface="#111a2e",
        bg_subtle="#1c2742",
        # Text
        text_primary="#e6edf7",
        text_muted="#8898b3",
        # Borders
        border_default="#2b3a5a",
        # Brand (brightened for dark surfaces)
        action_primary="#3b82f6",
        action_primary_dark="#1d4ed8",
        action_accent="#14b8a6",
        action_accent_subtle="rgba(15, 118, 110, 0.18)",
        action_cyan="#22d3ee",
        editable_focus_bg="#164e63",
        # State (brightened)
        state_success="#22c55e",
        state_warning="#fbbf24",
        state_danger="#f87171",
        state_info="#60a5fa",
        focus_ring="#14b8a6",
        disabled_fg="#475569",
        white="#ffffff",
        # M1 additive fields
        text_secondary="#b7c2d6",
        text_inverse="#0f172a",
        bg_surface_2="#16223a",
        bg_elevated="#18223a",
        border_soft="#1f2a44",
        border_strong="#44557a",
        bg_glass="rgba(17, 26, 46, 0.72)",
        bg_overlay="rgba(2, 6, 23, 0.7)",
        shadow_low="0 1px 2px rgba(0, 0, 0, 0.4)",
        shadow_medium="0 4px 12px rgba(0, 0, 0, 0.45)",
        shadow_high="0 12px 32px rgba(0, 0, 0, 0.5)",
    )


@dataclass(frozen=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class RadiusTokens:
    # Legacy fields
    control: int = 6
    dialog: int = 10
    # M1 additive (mockup vocabulary)
    field: int = 8
    card: int = 12
    pill: int = 999


@dataclass(frozen=True)
class TypographyTokens:
    family: str = "Segoe UI, Helvetica Neue, Arial"
    size_pt: int = 10
    title_size_pt: int = 14
    helper_size_pt: int = 8


@dataclass(frozen=True)
class MotionTokens:
    """Animation durations + default easing (consumed in M8).

    Values are deliberately short — Qt animation cost is dominated by
    paint, and over 200 ms motion feels sluggish on Windows desktops.
    """

    fast_ms: int = 120
    base_ms: int = 200
    easing: str = "OutCubic"


@dataclass(frozen=True)
class DesignTokens:
    colors: ColorTokens = field(default_factory=ColorTokens)
    spacing: SpacingTokens = field(default_factory=SpacingTokens)
    radius: RadiusTokens = field(default_factory=RadiusTokens)
    typography: TypographyTokens = field(default_factory=TypographyTokens)
    motion: MotionTokens = field(default_factory=MotionTokens)


def _hex_or_default(value: str, default: str) -> str:
    return value if HEX_COLOR_RE.match(value) else default


def relative_luminance(hex_color: str) -> float:
    """Return WCAG relative luminance for a hex colour."""
    value = hex_color.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Return WCAG contrast ratio between two hex colours."""
    lighter = max(relative_luminance(foreground), relative_luminance(background))
    darker = min(relative_luminance(foreground), relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def is_dark_color(hex_color: str) -> bool:
    """Return True when light content is needed on the colour."""
    return relative_luminance(hex_color) < 0.28


def build_design_tokens(cfg: AppConfig) -> DesignTokens:
    """Build semantic tokens from config-backed theme overrides.

    Legacy entry point — preserves the original "background colour drives
    dark inversion" behaviour. Used by the admin window, PDF report,
    colour-customisation dialog, and the legacy ``build_app_stylesheet``.
    For the new explicit-theme path, see ``build_design_tokens_for_theme``.
    """
    defaults = ColorTokens()
    bg_app = _hex_or_default(cfg.background, defaults.bg_app)
    dark_background = is_dark_color(bg_app)
    colors = ColorTokens(
        bg_app=bg_app,
        bg_surface="#111827" if dark_background else defaults.bg_surface,
        bg_subtle="#1f2937" if dark_background else defaults.bg_subtle,
        text_primary="#f8fafc" if dark_background else defaults.text_primary,
        text_muted="#cbd5e1" if dark_background else defaults.text_muted,
        border_default="#64748b" if dark_background else defaults.border_default,
        action_primary=_hex_or_default(cfg.primary_color, defaults.action_primary),
        action_primary_dark=defaults.action_primary_dark,
        action_accent=_hex_or_default(cfg.accent_color, defaults.action_accent),
        action_accent_subtle="#134e4a" if dark_background else defaults.action_accent_subtle,
        action_cyan=defaults.action_cyan,
        editable_focus_bg="#164e63" if dark_background else defaults.editable_focus_bg,
        state_success=defaults.state_success,
        state_warning=defaults.state_warning,
        state_danger=defaults.state_danger,
        state_info=defaults.state_info,
        focus_ring=_hex_or_default(cfg.accent_color, defaults.focus_ring),
        disabled_fg=defaults.disabled_fg,
        white=defaults.white,
    )
    typography = TypographyTokens(
        family=cfg.font_family or TypographyTokens.family,
        size_pt=cfg.font_size,
    )
    return DesignTokens(colors=colors, typography=typography)


def build_design_tokens_for_theme(cfg: AppConfig, theme: Theme) -> DesignTokens:
    """Build semantic tokens for an **explicit** theme.

    Unlike ``build_design_tokens``, this ignores ``cfg.background`` —
    the theme parameter is authoritative. Brand colours
    (``primary_color`` / ``accent_color``) from config still apply
    so customers keep their visual identity in both themes.

    ``Theme.SYSTEM`` is treated as ``Theme.LIGHT`` here; resolution of
    SYSTEM happens in ``ThemeService`` where ``QGuiApplication`` is
    available.
    """
    defaults = dark_color_tokens() if theme == Theme.DARK else ColorTokens()
    primary = _hex_or_default(cfg.primary_color, defaults.action_primary)
    accent = _hex_or_default(cfg.accent_color, defaults.action_accent)
    colors = replace(
        defaults,
        action_primary=primary,
        action_accent=accent,
        focus_ring=accent,
    )
    typography = TypographyTokens(
        family=cfg.font_family or TypographyTokens.family,
        size_pt=cfg.font_size,
    )
    return DesignTokens(colors=colors, typography=typography)

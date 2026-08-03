"""Design-system primitives for the Qt Widgets UI."""
from .accessibility import refresh_style, set_accessibility, set_ui_property
from .brand import select_logo_variant
from .commands import CommandDescriptor, apply_action_descriptor, set_action_enabled
from .material_palette import MaterialColor, all_known_grades, material_color
from .status import StatusBanner
from .tokens import (
    DesignTokens,
    Theme,
    build_design_tokens,
    build_design_tokens_for_theme,
    dark_color_tokens,
)

__all__ = [
    "CommandDescriptor",
    "DesignTokens",
    "MaterialColor",
    "StatusBanner",
    "Theme",
    "all_known_grades",
    "apply_action_descriptor",
    "build_design_tokens",
    "build_design_tokens_for_theme",
    "dark_color_tokens",
    "material_color",
    "refresh_style",
    "select_logo_variant",
    "set_accessibility",
    "set_action_enabled",
    "set_ui_property",
]

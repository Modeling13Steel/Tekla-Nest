"""Loads config.yaml into a frozen singleton.

Every module reads from here. Change config.yaml to rebrand — not code.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_CONFIG: AppConfig | None = None


def _resolve_base_dir() -> Path:
    """Find the project root, whether running from source or a PyInstaller bundle."""
    # PyInstaller sets sys._MEIPASS to the temp extraction folder
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # Normal source: config/ -> tekla_nest/ -> src/ -> project root
    return Path(__file__).resolve().parent.parent


_BASE_DIR = _resolve_base_dir()


@dataclass
class AppConfig:
    """Application configuration — populated from config.yaml."""

    # Branding
    title: str = "Nest Optimizer"
    logo_path: Path = field(
        default_factory=lambda: _BASE_DIR / "resources" / "logo_original_modern.svg"
    )
    icon_path: Path = field(
        default_factory=lambda: _BASE_DIR / "resources" / "logo_cut_bar_mark.ico"
    )
    version: str = "2.1.0"
    language: str = "en"

    # Theme
    primary_color: str = "#1d4ed8"
    accent_color: str = "#0f766e"
    background: str = "#f6f8fb"
    font_family: str = "Segoe UI, Helvetica Neue, Arial"
    font_size: int = 10

    # Report
    report_title: str = "Plano de Corte"
    company_name: str = ""
    report_logo_path: Path = field(
        default_factory=lambda: _BASE_DIR / "resources" / "logo_original_modern.svg"
    )
    report_template_path: Path = field(
        default_factory=lambda: _BASE_DIR / "resources" / "report_template.html"
    )
    show_material: bool = True
    show_stock_source: bool = True

    # Algorithm
    kerf_width: float = 0.0
    scrap_threshold: float = 2000.0
    max_strategies: int = 6

    # Stock defaults
    hot_rolled_families: list[str] = field(
        default_factory=lambda: ["HEB", "HEA", "HEM", "IPE", "IPN", "UPN", "UPE"]
    )
    hot_rolled_lengths: list[float] = field(
        default_factory=lambda: [6100, 10100, 12100, 14100, 15100, 16100]
    )
    other_lengths: list[float] = field(default_factory=lambda: [6000, 12000])
    default_stock_quantity: int = 100
    materials: list[str] = field(default_factory=lambda: ["S235JR", "S275JR", "S355JR"])

    # CSV
    csv_separators: list[str] = field(default_factory=lambda: [",", ";"])

    # Licensing
    license_server_url: str = ""
    revalidation_days: int = 30
    license_required: bool = False

    # Accessibility / motion
    prefer_reduced_motion: bool = False


class ConfigError(Exception):
    """Raised when config.yaml has problems.

    The message always includes:
      - Which key is wrong
      - What value was found
      - What was expected
    """


def _read_yaml(config_path: Path) -> dict:
    """Read and parse a YAML file with descriptive errors."""
    try:
        import yaml
    except ImportError:
        raise ConfigError(
            "PyYAML is not installed. Run:  uv pip install PyYAML   (or:  pip install PyYAML)"
        )

    try:
        text = config_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(
            f"config.yaml at '{config_path}' is not valid UTF-8.\n"
            f"  Detail: {exc}\n"
            f"  Fix: Re-save the file as UTF-8 (without BOM)."
        )
    except OSError as exc:
        raise ConfigError(
            f"Cannot read config.yaml at '{config_path}'.\n"
            f"  Detail: {exc}\n"
            f"  Fix: Check file permissions and path."
        )

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"config.yaml at '{config_path}' contains invalid YAML.\n"
            f"  Detail: {exc}\n"
            f"  Fix: Validate the file at https://www.yamllint.com/"
        )

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"config.yaml must be a YAML mapping (dict), got {type(raw).__name__}.\n"
            f"  Fix: The file should start with key-value pairs, not a list."
        )
    return raw


def _expect_type(section: str, key: str, value: object, expected: type) -> None:
    """Raise ConfigError if value is not the expected type."""
    if not isinstance(value, expected):
        raise ConfigError(
            f"config.yaml [{section}] key '{key}': "
            f"expected {expected.__name__}, got {type(value).__name__} = {value!r}"
        )


def _apply_section(cfg: AppConfig, raw: dict, section: str, mappings: dict, base_dir: Path) -> None:
    """Apply a config section's values to cfg with type checking."""
    data = raw.get(section, {})
    if not isinstance(data, dict):
        raise ConfigError(
            f"config.yaml section '{section}' must be a mapping, got {type(data).__name__}."
        )
    for yaml_key, (attr, converter) in mappings.items():
        if yaml_key in data:
            val = data[yaml_key]
            try:
                setattr(cfg, attr, converter(val, base_dir))
            except (ValueError, TypeError) as exc:
                raise ConfigError(
                    f"config.yaml [{section}] key '{yaml_key}': invalid value {val!r} — {exc}"
                )


# Converter helpers
def _str(v: object, _bd: Path) -> str:
    return str(v)


def _int(v: object, _bd: Path) -> int:
    return int(v)


def _float(v: object, _bd: Path) -> float:
    return float(v)


def _bool(v: object, _bd: Path) -> bool:
    if isinstance(v, bool):
        return v
    raise TypeError(f"expected true/false, got {type(v).__name__}")


def _path(v: object, bd: Path) -> Path:
    return bd / str(v)


def _str_list(v: object, _bd: Path) -> list[str]:
    if not isinstance(v, list):
        raise TypeError(f"expected a list, got {type(v).__name__}")
    return [str(x) for x in v]


def _float_list(v: object, _bd: Path) -> list[float]:
    if not isinstance(v, list):
        raise TypeError(f"expected a list, got {type(v).__name__}")
    return [float(x) for x in v]


def load_config(path: str | None = None) -> AppConfig:
    """Load config from YAML. Falls back to defaults if file is missing.

    Args:
        path: Explicit path to config.yaml. If None, looks in the project root.

    Returns:
        Populated AppConfig singleton.

    Raises:
        ConfigError: If the file exists but has invalid content, with a
                     descriptive message explaining exactly what is wrong.
    """
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    cfg = AppConfig()
    config_path = Path(path) if path else _BASE_DIR / "config.yaml"

    if not config_path.exists():
        _CONFIG = cfg
        return _CONFIG

    raw = _read_yaml(config_path)
    base_dir = config_path.parent

    # ── app section ──
    _apply_section(
        cfg,
        raw,
        "app",
        {
            "title": ("title", _str),
            "logo": ("logo_path", _path),
            "icon": ("icon_path", _path),
            "version": ("version", _str),
            "language": ("language", _str),
            "prefer_reduced_motion": ("prefer_reduced_motion", _bool),
        },
        base_dir,
    )

    # ── theme section ──
    _apply_section(
        cfg,
        raw,
        "theme",
        {
            "primary_color": ("primary_color", _str),
            "accent_color": ("accent_color", _str),
            "background": ("background", _str),
            "font_family": ("font_family", _str),
            "font_size": ("font_size", _int),
        },
        base_dir,
    )

    # ── report section ──
    _apply_section(
        cfg,
        raw,
        "report",
        {
            "title": ("report_title", _str),
            "company_name": ("company_name", _str),
            "logo": ("report_logo_path", _path),
            "template": ("report_template_path", _path),
            "show_material": ("show_material", _bool),
            "show_stock_source": ("show_stock_source", _bool),
        },
        base_dir,
    )

    # ── nesting section ──
    _apply_section(
        cfg,
        raw,
        "nesting",
        {
            "kerf_width": ("kerf_width", _float),
            "scrap_threshold": ("scrap_threshold", _float),
            "max_strategies": ("max_strategies", _int),
        },
        base_dir,
    )

    # ── stock_defaults section (nested) ──
    stock = raw.get("stock_defaults", {})
    if isinstance(stock, dict):
        hr = stock.get("hot_rolled_profiles", {})
        if isinstance(hr, dict):
            if "families" in hr:
                cfg.hot_rolled_families = _str_list(hr["families"], base_dir)
            if "lengths" in hr:
                cfg.hot_rolled_lengths = _float_list(hr["lengths"], base_dir)
            if "default_quantity" in hr:
                cfg.default_stock_quantity = _int(hr["default_quantity"], base_dir)
        ot = stock.get("other_profiles", {})
        if isinstance(ot, dict) and "lengths" in ot:
            cfg.other_lengths = _float_list(ot["lengths"], base_dir)
        if "materials" in stock:
            cfg.materials = _str_list(stock["materials"], base_dir)

    # ── csv section ──
    csv_sec = raw.get("csv", {})
    if isinstance(csv_sec, dict) and "separators" in csv_sec:
        cfg.csv_separators = _str_list(csv_sec["separators"], base_dir)

    # ── licensing section ──
    _apply_section(
        cfg,
        raw,
        "licensing",
        {
            "server_url": ("license_server_url", _str),
            "revalidation_days": ("revalidation_days", _int),
            "required": ("license_required", _bool),
        },
        base_dir,
    )

    _CONFIG = cfg
    return _CONFIG


def get_config() -> AppConfig:
    """Get the loaded config. Calls load_config() on first access."""
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def reset_config() -> None:
    """Reset the singleton — used in tests only."""
    global _CONFIG
    _CONFIG = None

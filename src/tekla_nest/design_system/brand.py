"""Brand asset selection helpers."""
from __future__ import annotations

from pathlib import Path

from .tokens import is_dark_color


def select_logo_variant(logo_path: Path, background: str) -> Path:
    """Choose a light/dark logo colourway for the active background."""
    if not logo_path.exists():
        return logo_path

    if is_dark_color(background):
        inverse = _with_suffix_before_extension(logo_path, "_inverse")
        if inverse.exists():
            return inverse
        return logo_path

    if logo_path.stem.endswith("_inverse"):
        normal = logo_path.with_name(
            f"{logo_path.stem.removesuffix('_inverse')}{logo_path.suffix}"
        )
        if normal.exists():
            return normal
    return logo_path


def _with_suffix_before_extension(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}{suffix}{path.suffix}")

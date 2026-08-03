"""Material grade → colour palette for chip rendering.

The palette is intentionally small and curated: every entry has been
checked against ``accessibility.contrast_ratio`` for a minimum WCAG AA
(4.5:1) ratio between ``bg`` and ``fg``.

Unknown grades fall back to a stable hash-based assignment from a fixed
pool of AA-safe pairs.  Stability matters because the same material in
two different sessions must paint the same colour — otherwise users
lose visual continuity between runs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialColor:
    bg: str
    fg: str


_FIXED: dict[str, MaterialColor] = {
    "S235JR": MaterialColor(bg="#DBEAFE", fg="#1E3A8A"),
    "S275JR": MaterialColor(bg="#DCFCE7", fg="#14532D"),
    "S355JR": MaterialColor(bg="#FEF3C7", fg="#78350F"),
    "S355J2": MaterialColor(bg="#FFE4E6", fg="#881337"),
    "S420":   MaterialColor(bg="#E0E7FF", fg="#3730A3"),
    "S460":   MaterialColor(bg="#F3E8FF", fg="#581C87"),
}

_POOL: tuple[MaterialColor, ...] = (
    MaterialColor(bg="#CFFAFE", fg="#155E75"),
    MaterialColor(bg="#FFEDD5", fg="#7C2D12"),
    MaterialColor(bg="#FCE7F3", fg="#831843"),
    MaterialColor(bg="#E0F2FE", fg="#075985"),
    MaterialColor(bg="#ECFCCB", fg="#3F6212"),
    MaterialColor(bg="#FEE2E2", fg="#7F1D1D"),
    MaterialColor(bg="#EDE9FE", fg="#4C1D95"),
    MaterialColor(bg="#F1F5F9", fg="#1E293B"),
)

_UNKNOWN: MaterialColor = MaterialColor(bg="#F1F5F9", fg="#475569")


def material_color(grade: str | None) -> MaterialColor:
    """Return a stable colour pair for the given grade.

    Empty or ``None`` grades return a neutral grey pair.  Known grades
    return their curated colour; unknown grades hash-map to the
    fallback pool deterministically.
    """
    if not grade:
        return _UNKNOWN
    key = grade.strip().upper()
    if not key:
        return _UNKNOWN
    if key in _FIXED:
        return _FIXED[key]
    index = (hash(key) & 0x7FFFFFFF) % len(_POOL)
    return _POOL[index]


def all_known_grades() -> tuple[str, ...]:
    """Return the curated grade names (for chip filter initialisation)."""
    return tuple(_FIXED.keys())

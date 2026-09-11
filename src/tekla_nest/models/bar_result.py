from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BarResult:
    """Result: a single stock bar with its assigned cuts.

    Migrated from: C# BarraPerfil class in FrmNest.cs
    """

    original_length: float
    mark: str
    material: str
    source: str
    cuts: list[float] = field(default_factory=list)
    cut_marks: list[str] = field(default_factory=list)
    priority: int = 0
    kerf_used: float = 0.0
    """Total kerf material consumed between cuts on this bar.

    Kept separate from ``cuts`` so that list always holds the *actual*
    piece lengths (what CSV/Excel/PDF exports should show), while kerf
    is still correctly deducted from capacity via ``free_length``/
    ``used_length``.
    """

    @property
    def free_length(self) -> float:
        return self.original_length - self.used_length

    @property
    def used_length(self) -> float:
        return sum(self.cuts) + self.kerf_used

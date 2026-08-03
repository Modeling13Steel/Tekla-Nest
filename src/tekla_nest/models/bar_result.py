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

    @property
    def free_length(self) -> float:
        return self.original_length - sum(self.cuts)

    @property
    def used_length(self) -> float:
        return sum(self.cuts)

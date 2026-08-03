from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bar_result import BarResult
    from .cut_piece import CutPiece


@dataclass
class ProfileResult:
    """Nesting result for a single profile (e.g. all HEA240 bars).

    Migrated from: C# ListaBarraPerfil class in FrmNest.cs
    """

    profile: str
    bars: list[BarResult] = field(default_factory=list)
    waste_pct: float = 0.0
    scrap_pct: float = 0.0  # waste from remnants <= scrap_threshold
    unfit_pieces: list[CutPiece] = field(default_factory=list)
    material: str = ""

    @property
    def has_unfit_pieces(self) -> bool:
        return bool(self.unfit_pieces)

    @property
    def total_stock_length(self) -> float:
        return sum(b.original_length for b in self.bars)

    @property
    def total_waste(self) -> float:
        return sum(b.free_length for b in self.bars)

    @property
    def utilization_pct(self) -> float:
        return 100.0 - self.waste_pct


@dataclass
class NestResult:
    """Complete nesting result across all profiles.

    Migrated from: DataTable resultado return + Percentagemdedesperdicio side-effects
    """

    profiles: list[ProfileResult] = field(default_factory=list)

    @property
    def overall_waste_pct(self) -> float:
        total_stock = sum(p.total_stock_length for p in self.profiles)
        total_waste = sum(p.total_waste for p in self.profiles)
        if total_stock == 0:
            return 0.0
        return (total_waste / total_stock) * 100.0

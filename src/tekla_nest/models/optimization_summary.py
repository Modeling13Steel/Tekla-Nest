"""OptimizationSummary — view-model derived from ``NestResult``.

KPI widgets bind to this object, **not** to ``NestResult`` itself, so the
view layer never imports engine types. New KPIs are added by extending
this dataclass and updating the strip — no view-layer changes to the
engine are required.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .nest_result import NestResult


@dataclass(frozen=True)
class OptimizationSummary:
    """Compact summary of a completed optimisation run."""

    waste_pct: float
    bars_used: int
    unfit_count: int
    profile_count: int

    @classmethod
    def from_nest_result(cls, result: NestResult | None) -> OptimizationSummary | None:
        """Build a summary from a ``NestResult``. Returns ``None`` for ``None``."""
        if result is None or not getattr(result, "profiles", None):
            return None
        profiles = result.profiles
        bars_used = sum(len(p.bars) for p in profiles)
        unfit_count = sum(len(p.unfit_pieces) for p in profiles)
        return cls(
            waste_pct=result.overall_waste_pct,
            bars_used=bars_used,
            unfit_count=unfit_count,
            profile_count=len(profiles),
        )

    @property
    def has_unfit(self) -> bool:
        return self.unfit_count > 0

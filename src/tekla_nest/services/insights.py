"""Heuristic insights derived from a ``NestResult``.

Pure functions — no I/O, no network, no LLM. Each heuristic returns a
list of :class:`Insight` records that the UI (or any future report
generator) can render. The presenter is responsible for wiring an
insight's optional ``action`` to a slot.

Insights in v2.1 (locked scope; future heuristics land in v2.2):
  * **add_stock** — at least one profile has ``unfit_pieces``; suggest
    sourcing a bar long enough to fit the largest unfit piece.
  * **high_waste** — a single profile shows > 25 % waste; suggest
    stocking shorter bars to improve utilisation.
  * **mixed_materials** — the same profile uses more than one material;
    suggest re-grouping to reduce setup cost.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from ..models import NestResult, ProfileResult

HIGH_WASTE_THRESHOLD_PCT = 25.0


@dataclass(frozen=True)
class Insight:
    """A single heuristic suggestion.

    ``severity`` mirrors the QSS state vocabulary: ``info`` for
    informational, ``warning`` for amber, ``danger`` for red. ``action``
    is the ``command_id`` of a presenter method the sidebar should
    surface as a button — ``None`` means render the insight read-only.
    ``context`` is a small dict the action consumer can read; values are
    primitive types so the dataclass stays hashable-when-frozen-callers
    don't need it (we don't, but keep ``eq=True``).
    """

    insight_id: str
    severity: str  # one of: info | warning | danger
    title_key: str  # i18n key for the title
    detail_key: str  # i18n key for the body text (may use placeholders)
    profile: str = ""
    action: str | None = None
    context: tuple[tuple[str, object], ...] = field(default_factory=tuple)

    def context_dict(self) -> dict[str, object]:
        return dict(self.context)


# ── Heuristics ────────────────────────────────────────────────────


def _add_stock_insights(profiles: Iterable[ProfileResult]) -> list[Insight]:
    out: list[Insight] = []
    for profile in profiles:
        if not profile.unfit_pieces:
            continue
        longest = max(profile.unfit_pieces, key=lambda p: p.length)
        out.append(
            Insight(
                insight_id=f"add_stock:{profile.profile}",
                severity="warning",
                title_key="insights.add_stock.title",
                detail_key="insights.add_stock.detail",
                profile=profile.profile,
                action="request_stock",
                context=(
                    ("profile", profile.profile),
                    ("length", float(longest.length)),
                    ("piece_count", len(profile.unfit_pieces)),
                ),
            )
        )
    return out


def _high_waste_insights(profiles: Iterable[ProfileResult]) -> list[Insight]:
    out: list[Insight] = []
    for profile in profiles:
        if profile.waste_pct <= HIGH_WASTE_THRESHOLD_PCT:
            continue
        out.append(
            Insight(
                insight_id=f"high_waste:{profile.profile}",
                severity="warning",
                title_key="insights.high_waste.title",
                detail_key="insights.high_waste.detail",
                profile=profile.profile,
                action=None,
                context=(
                    ("profile", profile.profile),
                    ("waste_pct", float(profile.waste_pct)),
                ),
            )
        )
    return out


def _mixed_materials_insights(profiles: Iterable[ProfileResult]) -> list[Insight]:
    out: list[Insight] = []
    for profile in profiles:
        materials = {bar.material for bar in profile.bars if bar.material}
        if len(materials) <= 1:
            continue
        out.append(
            Insight(
                insight_id=f"mixed_materials:{profile.profile}",
                severity="info",
                title_key="insights.mixed_materials.title",
                detail_key="insights.mixed_materials.detail",
                profile=profile.profile,
                action=None,
                context=(
                    ("profile", profile.profile),
                    ("material_count", len(materials)),
                    ("materials", tuple(sorted(materials))),
                ),
            )
        )
    return out


# ── Public entry point ────────────────────────────────────────────


def suggest(result: NestResult | None) -> list[Insight]:
    """Run every heuristic on ``result`` and return the merged list.

    Order: ``add_stock`` first (most actionable), then ``high_waste``,
    then ``mixed_materials``. Callers may stable-re-sort by severity if
    they want danger first.
    """
    if result is None or not result.profiles:
        return []
    profiles = list(result.profiles)
    return [
        *_add_stock_insights(profiles),
        *_high_waste_insights(profiles),
        *_mixed_materials_insights(profiles),
    ]

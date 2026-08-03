"""Shared bar/purchase aggregation for the report stack.

Single source of truth for grouping a ``NestResult`` by
``(profile, material, length, source)`` and computing operator-prep
totals. Used by:

- ``views.purchase_table.PurchaseTableWidget`` (in-app tab)
- ``services.csv_report`` (CSV Purchase section)
- ``services.excel_report`` (Purchase sheet)
- ``services.pdf_report`` / ``resources/report_template.html`` (PDF prep header)

Lifting this here keeps the contract identical across surfaces — the
fix for feedback v2 #2/#2.1/#6 hinges on the four exports agreeing on
the same numbers.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from ..models import NestResult

# A scope is either ``None`` (= keep everything) or a frozenset of
# ``(profile, material)`` pairs to retain. Profile / material strings
# compared case-insensitively after stripping.
ReportScope = frozenset[tuple[str, str]] | None


@dataclass(frozen=True)
class PurchaseRow:
    """One distinct stock bar to acquire."""
    profile: str
    material: str
    length: float
    source: str
    count: int

    @property
    def total_mm(self) -> float:
        return self.length * self.count

    @property
    def linear_m(self) -> float:
        return self.total_mm / 1000.0


@dataclass(frozen=True)
class ProfilePrep:
    """Operator-prep summary for a single profile-section.

    ``by_length`` is ordered descending by length so the rack-prep flow
    reads naturally (grab the longest bars first).
    """
    profile: str
    material: str
    by_length: list[tuple[float, int]]
    total_bars: int
    linear_m: float


def _key(profile: str, material: str) -> tuple[str, str]:
    return (
        (profile or "").strip().lower(),
        (material or "").strip().lower(),
    )


def filter_result(result: NestResult, scope: ReportScope) -> NestResult:
    """Return a shallow-cloned NestResult containing only ``scope`` profiles.

    ``scope=None`` returns the input unchanged. An empty frozenset
    returns an empty NestResult — the caller must treat that as an
    invalid selection (UI should warn before exporting).
    """
    if scope is None:
        return result
    keep = filter_profiles(result, scope)
    return NestResult(profiles=keep)


def filter_profiles(result: NestResult, scope: ReportScope) -> list:
    """Return the subset of ``result.profiles`` matching ``scope``.

    ``scope=None`` returns the full list (no filtering). An empty
    frozenset returns an empty list — the caller must treat that as an
    invalid selection, not "all".
    """
    if scope is None:
        return list(result.profiles)
    return [
        p for p in result.profiles
        if _key(p.profile, p.material) in scope
    ]


def available_scope_keys(result: NestResult) -> list[tuple[str, str]]:
    """Distinct ``(profile, material)`` keys in stable display order.

    Returned with original casing for display; callers wanting to filter
    must lower-case via ``_key`` before building the scope frozenset.
    """
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for p in result.profiles:
        k = _key(p.profile, p.material)
        if k in seen:
            continue
        seen.add(k)
        out.append((p.profile, p.material or ""))
    return out


def aggregate_purchase(
    result: NestResult,
    scope: ReportScope = None,
) -> list[PurchaseRow]:
    """Bucket bars by (profile, material, length, source).

    Stable order: profile asc · material asc · length DESC · source asc.
    Length DESC matches the procurement workflow (longest bars first).
    """
    profiles = filter_profiles(result, scope)
    buckets: dict[tuple[str, str, float, str], int] = defaultdict(int)
    for profile in profiles:
        for bar in profile.bars:
            key = (
                profile.profile,
                profile.material or bar.material,
                float(bar.original_length),
                bar.source,
            )
            buckets[key] += 1
    rows = [
        PurchaseRow(profile=p, material=m, length=ln, source=src, count=c)
        for (p, m, ln, src), c in buckets.items()
    ]
    rows.sort(key=lambda r: (r.profile, r.material, -r.length, r.source))
    return rows


def aggregate_prep(
    result: NestResult,
    scope: ReportScope = None,
) -> list[ProfilePrep]:
    """One ProfilePrep per (profile, material) — operator-facing.

    For each section, groups ``bar.original_length`` × count, ordered
    longest-first, plus a total-bars count and linear metres total.
    """
    profiles = filter_profiles(result, scope)
    out: list[ProfilePrep] = []
    for profile in profiles:
        by_len: dict[float, int] = defaultdict(int)
        for bar in profile.bars:
            by_len[float(bar.original_length)] += 1
        ordered = sorted(by_len.items(), key=lambda kv: -kv[0])
        total_bars = sum(by_len.values())
        linear_m = sum(ln * c for ln, c in by_len.items()) / 1000.0
        out.append(ProfilePrep(
            profile=profile.profile,
            material=profile.material or "",
            by_length=ordered,
            total_bars=total_bars,
            linear_m=linear_m,
        ))
    return out


def grand_totals(rows: Iterable[PurchaseRow]) -> tuple[int, float]:
    """Return (total_bars, total_linear_m) across the given rows."""
    rows = list(rows)
    return sum(r.count for r in rows), sum(r.linear_m for r in rows)

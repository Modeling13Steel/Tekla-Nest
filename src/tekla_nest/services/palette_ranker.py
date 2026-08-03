"""Pure ranking & history helpers for the command palette.

Lives under ``services/`` so the matcher is testable without a
``QApplication``. The palette dialog imports ``rank_commands`` and
``record_invocation`` — no other side-effects allowed here.

The matcher is a sub-sequence fuzzy scorer (M4 §10.7). We avoid a
``rapidfuzz`` dependency to keep the install footprint small.
"""
from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_HISTORY_CAP = 100
_RECENCY_HALF_LIFE_S = 7 * 24 * 3600  # one week
_PREFS_PATH = Path.home() / ".tekla_nest" / "preferences.json"
_HISTORY_KEY = "palette_history"


# ── Fuzzy matching ────────────────────────────────────────────────


def fuzzy_score(query: str, candidate: str) -> int | None:
    """Return a sub-sequence match score (higher = better) or ``None``.

    Empty query matches everything with score 0. The scoring rewards
    consecutive characters and word-start hits — mirrors the reference
    implementation in ROADMAP §10.7.
    """
    q, c = query.lower(), candidate.lower()
    if not q:
        return 0
    score, last = 0, -1
    for ch in q:
        idx = c.find(ch, last + 1)
        if idx == -1:
            return None
        score += 5 if idx == last + 1 else 1
        if idx == 0 or c[idx - 1] in " /:-_":
            score += 3
        last = idx
    return score - len(c) // 10


# ── Ranking ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class RankedCommand:
    """A command paired with its computed rank score."""

    command_id: str
    label: str
    score: int


def rank_commands(
    query: str,
    candidates: Iterable[tuple[str, str]],
    history: Iterable[tuple[str, float]] | None = None,
    *,
    now: float | None = None,
) -> list[RankedCommand]:
    """Filter and rank candidates.

    ``candidates`` is an iterable of ``(command_id, label)`` tuples.
    ``history`` is the persisted ``[(command_id, ts), ...]`` log; recency
    boosts ties. With an empty query, results are sorted by recency only
    (most recent first), preserving registration order for unseen items.
    """
    history_list = list(history or [])
    freq = _frequency_boost(history_list, now=now)

    ranked: list[RankedCommand] = []
    for cmd_id, label in candidates:
        if query:
            score = fuzzy_score(query, label)
            if score is None:
                continue
            score += freq.get(cmd_id, 0)
            ranked.append(RankedCommand(cmd_id, label, score))
        else:
            ranked.append(RankedCommand(cmd_id, label, freq.get(cmd_id, 0)))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def _frequency_boost(
    history: list[tuple[str, float]], *, now: float | None
) -> dict[str, int]:
    """Recency-decayed frequency. Older invocations contribute less."""
    if not history:
        return {}
    current = now if now is not None else time.time()
    weights: dict[str, float] = {}
    for cmd_id, ts in history:
        age = max(0.0, current - ts)
        weight = 0.5 ** (age / _RECENCY_HALF_LIFE_S)
        weights[cmd_id] = weights.get(cmd_id, 0.0) + weight
    # Map weights to a small integer score so they break score ties without
    # dominating a strong fuzzy match.
    return {cmd_id: int(round(w * 4)) for cmd_id, w in weights.items()}


# ── Persistence ───────────────────────────────────────────────────


def load_history(path: Path | None = None) -> list[tuple[str, float]]:
    """Read palette history from preferences. Returns ``[]`` on any error."""
    target = path or _PREFS_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    raw = data.get(_HISTORY_KEY, [])
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, float]] = []
    for item in raw:
        if isinstance(item, list) and len(item) == 2 and isinstance(item[0], str):
            try:
                out.append((item[0], float(item[1])))
            except (TypeError, ValueError):
                continue
    return out


def save_history(history: list[tuple[str, float]], path: Path | None = None) -> None:
    """Write palette history to preferences. Caps at ``_HISTORY_CAP`` items."""
    target = path or _PREFS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    capped = history[-_HISTORY_CAP:]
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            existing = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        existing = {}
    existing[_HISTORY_KEY] = [[cmd, ts] for cmd, ts in capped]
    target.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def record_invocation(
    command_id: str,
    history: list[tuple[str, float]],
    *,
    now: float | None = None,
) -> list[tuple[str, float]]:
    """Append an invocation and return the (possibly capped) new history."""
    ts = now if now is not None else time.time()
    new_history = [*history, (command_id, ts)]
    if len(new_history) > _HISTORY_CAP:
        new_history = new_history[-_HISTORY_CAP:]
    return new_history

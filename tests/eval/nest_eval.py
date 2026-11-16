"""Nesting eval: run the real app path on seeded instances and score it.

What it measures per instance
- gap to the exact optimum (small instances, subset DP), and to the
  material lower bound sum(pieces) (all instances)
- waste %, bars, purchased metres, runtime
- invariant violations: every piece placed once, no overfill, downsize is
  tight, client stock used before buying market bars, no two bars that
  could be merged into one cheaper bar

Run:  uv run python -m tests.eval.nest_eval [--seeds 30] [--trim 100] [--kerf 3]
Gate: tests/eval/test_nest_eval.py
"""
from __future__ import annotations

import argparse
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field

from tekla_nest.config.app_config import get_config
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.services.nest_engine import NestEngine
from tekla_nest.services.stock_rules import generate_default_stock

PROFILE, MATERIAL = "HEA240", "S275JR"  # hot-rolled -> config lengths


# ── Instances ────────────────────────────────────────────────────


@dataclass
class Instance:
    name: str
    parts: list[PartEntry]
    client: list[StockEntry] = field(default_factory=list)

    @property
    def pieces(self) -> list[float]:
        return [p.length for p in self.parts for _ in range(p.quantity)]


def _parts(rng: random.Random, n_marks: int, lo: int, hi: int, qty: int) -> list[PartEntry]:
    # Tekla lengths are usually whole mm, often round to 5/10.
    return [
        PartEntry(rng.randint(1, qty), float(rng.randint(lo, hi) // 5 * 5),
                  f"P{i}", PROFILE, MATERIAL)
        for i in range(n_marks)
    ]


FAMILIES = {
    # name: (marks, min mm, max mm, max qty per mark)
    "short": (6, 300, 3000, 3),
    "mixed": (6, 300, 9000, 2),
    "long": (5, 4000, 15000, 2),
    "big-mixed": (25, 300, 12000, 6),  # too big for exact DP, LB only
}


def make_instances(seeds: int) -> list[Instance]:
    out = []
    for seed in range(seeds):
        for fam, (n, lo, hi, q) in FAMILIES.items():
            rng = random.Random(f"{fam}-{seed}")
            out.append(Instance(f"{fam}#{seed}", _parts(rng, n, lo, hi, q)))
        # client-stock scenario: a few short offcuts in the yard
        rng = random.Random(f"client-{seed}")
        client = [StockEntry(rng.randint(1, 3), float(rng.choice([3000, 4500, 6000, 7500])),
                             0, PROFILE, MATERIAL, "Cliente")]
        out.append(Instance(f"client#{seed}", _parts(rng, 5, 500, 9000, 2), client))
    return out


# ── Exact optimum (market stock only, unlimited qty) ──────────────


def optimal_purchase(pieces: list[float], lengths: list[float], kerf: float) -> float | None:
    """Min total purchased mm. Subset DP, O(3^n): keep n <= ~13."""
    n = len(pieces)
    if n > 13:
        return None
    lengths = sorted(lengths)
    full = (1 << n) - 1
    used = [0.0] * (1 << n)
    cnt = [0] * (1 << n)
    for m in range(1, full + 1):
        low = m & -m
        i = low.bit_length() - 1
        used[m] = used[m ^ low] + pieces[i]
        cnt[m] = cnt[m ^ low] + 1
    bar_cost = [0.0] * (1 << n)
    for m in range(1, full + 1):
        need = used[m] + kerf * (cnt[m] - 1)
        bar_cost[m] = next((L for L in lengths if L >= need), float("inf"))
    inf = float("inf")
    best = [inf] * (1 << n)
    best[0] = 0.0
    for m in range(1, full + 1):
        low = m & -m
        rest = m ^ low
        s = rest
        while True:  # every submask of m that contains its lowest bit
            sub = s | low
            c = bar_cost[sub]
            if c != inf:
                v = c + best[m ^ sub]
                if v < best[m]:
                    best[m] = v
            if s == 0:
                break
            s = (s - 1) & rest
    return best[full] if best[full] != inf else None


# ── Run + score ──────────────────────────────────────────────────


@dataclass
class Score:
    name: str
    bars: int
    purchased_mm: float  # market bars only, nominal length
    waste_pct: float
    lb_gap_pct: float
    opt_gap_pct: float | None
    ms: float
    violations: list[str]


def run(inst: Instance, kerf: float = 0.0, trim: float = 0.0) -> Score:
    """``trim`` simulates scrapping the bar ends: the engine sees L - trim,
    but purchase is still costed at the nominal L."""
    cfg = get_config()
    market = generate_default_stock([(PROFILE, MATERIAL)])
    for s in market:
        s.length -= trim
    engine = NestEngine(kerf_width=kerf, scrap_threshold=cfg.scrap_threshold,
                        max_strategies=cfg.max_strategies)
    t0 = time.perf_counter()
    res = NestPresenter._compute_nest_result(inst.parts, market, inst.client, engine)
    ms = (time.perf_counter() - t0) * 1000
    prof = res.profiles[0]
    lengths = sorted(cfg.hot_rolled_lengths)

    v: list[str] = []
    placed = Counter(c for b in prof.bars for c in b.cuts)
    if placed != Counter(inst.pieces) or prof.unfit_pieces:
        v.append(f"placement: {len(prof.unfit_pieces)} unfit / multiset mismatch")
    for b in prof.bars:
        if b.used_length > b.original_length + 1e-6:
            v.append(f"overfill {b.original_length}")
        if b.source == "Mercado":
            tighter = [L - trim for L in lengths if b.used_length <= L - trim < b.original_length]
            if tighter:
                v.append(f"loose downsize {b.original_length} -> {min(tighter)}")
    # client stock: an unused client bar that could carry a market bar's cuts
    client_avail = Counter(s.length for s in inst.client for _ in range(s.quantity))
    client_avail.subtract(b.original_length for b in prof.bars if b.source == "Cliente")
    spare = sorted(L for L, c in client_avail.items() for _ in range(max(c, 0)))
    for b in prof.bars:
        if b.source == "Mercado" and any(L >= b.used_length for L in spare):
            v.append(f"bought {b.original_length} while client bar fits")
            break
    # pair merge: two market bars whose cuts fit one shorter-total bar
    mk = [b for b in prof.bars if b.source == "Mercado"]
    for i in range(len(mk)):
        for j in range(i + 1, len(mk)):
            need = mk[i].used_length + mk[j].used_length + kerf
            one = next((L - trim for L in lengths if L - trim >= need), None)
            if one is not None and one < mk[i].original_length + mk[j].original_length:
                v.append(f"mergeable bars {mk[i].original_length}+{mk[j].original_length} -> {one}")
                break
        else:
            continue
        break

    nominal = {L - trim: L for L in lengths}
    purchased = sum(nominal.get(b.original_length, b.original_length)
                    for b in prof.bars if b.source == "Mercado")
    total_stock = sum(nominal.get(b.original_length, b.original_length) for b in prof.bars)
    need = sum(inst.pieces)
    client_mm = total_stock - purchased
    lb = max(need - sum(s.length * s.quantity for s in inst.client), 0) or 1
    opt = None if inst.client else optimal_purchase(inst.pieces, lengths if not trim
                                                    else [L - trim for L in lengths], kerf)
    if opt is not None and trim:
        opt = None  # trimmed optimum is costed differently; skip
    return Score(
        name=inst.name,
        bars=len(prof.bars),
        purchased_mm=purchased,
        waste_pct=(total_stock - need) / total_stock * 100 if total_stock else 0.0,
        lb_gap_pct=(purchased - lb) / lb * 100 if not inst.client else
        (purchased + client_mm - need) / need * 100,
        opt_gap_pct=(purchased - opt) / opt * 100 if opt else None,
        ms=ms,
        violations=v,
    )


def summarize(scores: list[Score]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for fam in sorted({s.name.split("#")[0] for s in scores}):
        rows = [s for s in scores if s.name.startswith(fam + "#")]
        gaps = [s.opt_gap_pct for s in rows if s.opt_gap_pct is not None]
        out[fam] = {
            "n": len(rows),
            "waste_pct": statistics.mean(s.waste_pct for s in rows),
            "opt_gap_mean": statistics.mean(gaps) if gaps else float("nan"),
            "opt_gap_max": max(gaps) if gaps else float("nan"),
            "at_optimum_pct": 100 * sum(g < 1e-9 for g in gaps) / len(gaps) if gaps else float("nan"),
            "violating_pct": 100 * sum(bool(s.violations) for s in rows) / len(rows),
            "purchased_m": sum(s.purchased_mm for s in rows) / 1000,
            "ms_max": max(s.ms for s in rows),
        }
    return out


def main() -> None:
    from tekla_nest.config.app_config import load_config

    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--kerf", type=float, default=0.0)
    ap.add_argument("--trim", type=float, default=0.0, help="mm scrapped per bar (e.g. 100)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("-v", action="store_true", help="list each violation")
    a = ap.parse_args()
    load_config(a.config)
    scores = [run(i, a.kerf, a.trim) for i in make_instances(a.seeds)]
    cols = ["n", "waste_pct", "opt_gap_mean", "opt_gap_max", "at_optimum_pct",
            "violating_pct", "purchased_m", "ms_max"]
    print(f"kerf={a.kerf} trim={a.trim} lengths={get_config().hot_rolled_lengths}")
    print(f"{'family':<10}" + "".join(f"{c:>15}" for c in cols))
    for fam, m in summarize(scores).items():
        print(f"{fam:<10}" + "".join(f"{m[c]:>15.2f}" for c in cols))
    if a.v:
        for s in scores:
            for msg in s.violations:
                print(f"  {s.name}: {msg}")


if __name__ == "__main__":
    main()

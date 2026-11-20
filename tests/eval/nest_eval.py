"""Nesting eval: run the real app path on seeded instances and score it
against a reference solver (tests/eval/reference.py, scipy/HiGHS).

Per instance (summed over its (profile, material) groups)
- purchased mm (market bars, nominal length) vs
  * lb:   valid lower bound (column generation, rounded to the stock gcd)
  * best: best-known integer (MILP over patterns, or the engine's own plan
          if that is better); ``proven`` when best == lb or MILP was exhaustive
  * opt:  exact optimum by subset DP (single-profile, market-only, n <= 13)
- invariant violations (hard: placement, overfill, stock availability,
  purchase below the lower bound) and smells (soft optimality hints: loose
  downsize, bought while a client bar fits, two mergeable bars)
- waste %, bars, engine runtime, reference runtime

Suites: small (random, the original families), medium / full (realistic
Tekla-style jobs, see projects.py), projects (tests/eval/projects/<name>/).

Run:  uv run python -m tests.eval.nest_eval [--suite small|medium|full|projects|all]
          [--seeds 30] [--kerf 3] [--trim 100] [--json out.json] [--compare old.json]
Gate: tests/eval/test_nest_eval.py (slow part: pytest -m eval_slow)
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass, field

from tekla_nest.config.app_config import get_config
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.services.nest_engine import NestEngine
from tekla_nest.services.stock_rules import generate_default_stock
from tests.eval import projects
from tests.eval.reference import StockType
from tests.eval.reference import solve as ref_solve

PROFILE, MATERIAL = "HEA240", "S275JR"  # hot-rolled -> config lengths
MARKET, CLIENT = "Mercado", "Cliente"


# ── Instances ────────────────────────────────────────────────────


@dataclass
class Instance:
    name: str  # "<family>#<seed>"
    parts: list[PartEntry]
    client: list[StockEntry] = field(default_factory=list)
    kerf: float | None = None  # overrides the run() kerf when set
    expected: dict = field(default_factory=dict)  # project fixtures only

    @property
    def family(self) -> str:
        return self.name.split("#")[0]

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
    "big-mixed": (25, 300, 12000, 6),  # too big for exact DP
}


def make_instances(seeds: int) -> list[Instance]:
    """The original small random families (single profile)."""
    out = []
    for seed in range(seeds):
        for fam, (n, lo, hi, q) in FAMILIES.items():
            rng = random.Random(f"{fam}-{seed}")
            out.append(Instance(f"{fam}#{seed}", _parts(rng, n, lo, hi, q)))
        # client-stock scenario: a few short offcuts in the yard
        rng = random.Random(f"client-{seed}")
        client = [StockEntry(rng.randint(1, 3), float(rng.choice([3000, 4500, 6000, 7500])),
                             0, PROFILE, MATERIAL, CLIENT)]
        out.append(Instance(f"client#{seed}", _parts(rng, 5, 500, 9000, 2), client))
    return out


def make_realistic(size: str, seeds: int) -> list[Instance]:
    return [Instance(f"{fam}#{seed}", parts, client, kerf)
            for fam, seed, parts, client, kerf in projects.realistic(size, seeds)]


def make_projects() -> list[Instance]:
    out = []
    for d in projects.project_dirs():
        parts, client, expected = projects.load_project(d)
        out.append(Instance(f"project:{d.name}#0", parts, client,
                            expected.get("kerf_mm"), expected))
    return out


def make_suite(suite: str, seeds: int) -> list[Instance]:
    if suite == "all":
        return [i for s in ("small", "medium", "full", "projects") for i in make_suite(s, seeds)]
    return {"small": lambda: make_instances(seeds),
            "medium": lambda: make_realistic("medium", seeds),
            "full": lambda: make_realistic("full", seeds),
            "projects": make_projects}[suite]()


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
        bar_cost[m] = next((c for c in lengths if c >= need), float("inf"))
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
    family: str
    bars: int
    pieces: int
    unfit: int
    purchased_mm: float  # market bars only, nominal length
    waste_pct: float
    material_gap_pct: float  # vs sum(pieces) (minus client stock)
    opt_gap_pct: float | None  # vs exact optimum, when known
    lb_mm: float | None  # reference lower bound (None: reference skipped)
    best_mm: float | None  # best-known integer purchase
    gap_lb_pct: float | None
    gap_best_pct: float | None
    proven: bool
    ms: float  # engine (presenter path)
    ref_ms: float
    violations: list[str]  # hard: must never happen
    smells: list[str] = field(default_factory=list)  # soft optimality hints
    competitor_mm: float | None = None


def _gap(a: float, ref: float | None) -> float | None:
    if ref is None:
        return None
    return (a - ref) / ref * 100 if ref > 0 else (0.0 if a <= 1e-6 else 100.0)


def _check_group(prof, pieces, avail, kerf, trim):
    """Return (hard, soft) messages for one ProfileResult."""
    hard: list[str] = []
    soft: list[str] = []
    tag = f"{prof.profile}/{prof.material}"
    max_cap = max(L for L, _ in avail)
    fit = Counter(p for p in pieces if p <= max_cap)
    if Counter(c for b in prof.bars for c in b.cuts) != fit or \
            Counter(p.length for p in prof.unfit_pieces) != Counter(pieces) - fit:
        hard.append(f"{tag} placement: {len(prof.unfit_pieces)} unfit / multiset mismatch")
    used_stock = Counter((b.original_length, b.source) for b in prof.bars)
    for key, n in used_stock.items():
        if n > avail.get(key, 0):
            hard.append(f"{tag} uses {n}x {key} but only {avail.get(key, 0)} available")
    for b in prof.bars:
        need = sum(b.cuts) + kerf * (len(b.cuts) - 1)
        if need > b.original_length + 1e-6:
            hard.append(f"{tag} overfill {b.original_length}: needs {need}")
    caps = sorted(L for L, s in avail if s == MARKET)
    mk = [b for b in prof.bars if b.source == MARKET]
    for b in mk:
        tighter = [L for L in caps if b.used_length <= L < b.original_length]
        if tighter:
            soft.append(f"{tag} loose downsize {b.original_length} -> {min(tighter)}")
            break
    client_left = Counter({L: n for (L, s), n in avail.items() if s == CLIENT})
    client_left.subtract(b.original_length for b in prof.bars if b.source == CLIENT)
    if any(n > 0 and any(cap >= b.used_length for b in mk) for cap, n in client_left.items()):
        soft.append(f"{tag} bought a bar while a client bar fits its cuts")
    for i in range(len(mk)):  # two market bars whose cuts fit one cheaper bar
        for j in range(i + 1, len(mk)):
            need = mk[i].used_length + mk[j].used_length + kerf
            one = next((c for c in caps if c >= need), None)
            if one is not None and one + trim < mk[i].original_length + mk[j].original_length + 2 * trim:
                soft.append(f"{tag} mergeable bars {mk[i].original_length}+"
                            f"{mk[j].original_length} -> {one}")
                break
        else:
            continue
        break
    return hard, soft


def run(inst: Instance, kerf: float = 0.0, trim: float = 0.0,
        reference: bool = True, time_limit: float = 10.0) -> Score:
    """Nest ``inst`` through the real presenter path and score it.

    ``trim`` simulates scrapping the bar ends: the engine sees L - trim,
    but purchase is still costed at the nominal L. Market quantities are
    raised to at least the group's piece count (effectively unlimited, so
    the app default of 100 per length never binds).
    """
    kerf = inst.kerf if inst.kerf is not None else kerf
    cfg = get_config()
    groups = Counter()
    for p in inst.parts:
        groups[(p.profile, p.material)] += p.quantity
    market = generate_default_stock(sorted(groups))
    for s in market:
        s.length -= trim
        s.quantity = max(s.quantity, groups[(s.profile, s.material)])
    engine = NestEngine(kerf_width=kerf, scrap_threshold=cfg.scrap_threshold,
                        max_strategies=cfg.max_strategies)
    t0 = time.perf_counter()
    res = NestPresenter._compute_nest_result(inst.parts, market, inst.client, engine)
    ms = (time.perf_counter() - t0) * 1000

    hard: list[str] = []
    soft: list[str] = []
    purchased = total_stock = client_mm = ref_ms = 0.0
    lb = best = 0.0
    proven = True
    bars = unfit = 0
    for prof in res.profiles:
        gparts = [p for p in inst.parts
                  if p.profile == prof.profile and (p.material or "") == prof.material]
        pieces = [p.length for p in gparts for _ in range(p.quantity)]
        stock = NestPresenter._build_stock_for(prof.profile, prof.material, gparts,
                                               market, inst.client)
        bars += len(prof.bars)
        unfit += len(prof.unfit_pieces)
        g_buy = sum(b.original_length + trim for b in prof.bars if b.source == MARKET)
        purchased += g_buy
        total_stock += g_buy + sum(b.original_length for b in prof.bars if b.source != MARKET)
        client_mm += sum(b.original_length for b in prof.bars if b.source != MARKET)
        if not stock:
            hard.append(f"{prof.profile}/{prof.material}: no stock")
            continue
        avail = Counter((b.length, b.source) for b in stock)
        h, s = _check_group(prof, pieces, avail, kerf, trim)
        hard += h
        soft += s
        if not reference:
            continue
        max_cap = max(L for L, _ in avail)
        types = Counter(p for p in pieces if p <= max_cap)
        if not types:
            continue
        sts = [StockType(L, L + trim) if src == MARKET else StockType(L, 0.0, n)
               for (L, src), n in sorted(avail.items())]
        r = ref_solve(list(types), list(types.values()), sts, kerf, time_limit=time_limit)
        ref_ms += r.ms
        # the engine's own plan is a feasible upper bound when it is valid
        cands = [x for x in (r.best, None if h else g_buy) if x is not None]
        g_best = min(cands) if cands else None
        if g_buy < r.lb - 1e-6 and not h:
            hard.append(f"{prof.profile}/{prof.material} purchase {g_buy} below lower bound {r.lb}")
        lb += r.lb
        if g_best is None:
            best, proven = None, False
        elif best is not None:
            best += g_best
            proven = proven and (r.proven or g_best <= r.lb + 1e-6)

    if not reference:
        lb = best = None
        proven = False
    need = sum(p for p in inst.pieces)
    opt = None
    if not inst.client and not trim and len(res.profiles) == 1 and not unfit:
        prof = res.profiles[0]
        caps = sorted({b.length for b in NestPresenter._build_stock_for(
            prof.profile, prof.material, inst.parts, market, [])})
        opt = optimal_purchase(inst.pieces, caps, kerf)
    mat_lb = max(need - sum(s.length * s.quantity for s in inst.client), 0) or 1
    comp = inst.expected.get("competitor", {}).get("purchased_m")
    return Score(
        name=inst.name,
        family=inst.family,
        bars=bars,
        pieces=len(inst.pieces),
        unfit=unfit,
        purchased_mm=purchased,
        waste_pct=(total_stock - need) / total_stock * 100 if total_stock else 0.0,
        material_gap_pct=(purchased - mat_lb) / mat_lb * 100 if not inst.client else
        (purchased + client_mm - need) / need * 100,
        opt_gap_pct=_gap(purchased, opt) if opt else None,
        lb_mm=lb,
        best_mm=best,
        gap_lb_pct=_gap(purchased, lb),
        gap_best_pct=_gap(purchased, best),
        proven=proven,
        ms=ms,
        ref_ms=ref_ms,
        violations=hard,
        smells=soft,
        competitor_mm=comp * 1000 if comp is not None else None,
    )


def _stats(xs: list[float | None]) -> tuple[float, float]:
    xs = [x for x in xs if x is not None]
    return (statistics.mean(xs), max(xs)) if xs else (float("nan"), float("nan"))


def summarize(scores: list[Score]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for fam in sorted({s.family for s in scores}):
        rows = [s for s in scores if s.family == fam]
        gaps = [s.opt_gap_pct for s in rows if s.opt_gap_pct is not None]
        lb_mean, lb_max = _stats([s.gap_lb_pct for s in rows])
        best_mean, best_max = _stats([s.gap_best_pct for s in rows])
        opt_mean, opt_max = _stats(gaps)
        ms = [s.ms for s in rows]
        out[fam] = {
            "n": len(rows),
            "pieces": statistics.mean(s.pieces for s in rows),
            "purchased_m": sum(s.purchased_mm for s in rows) / 1000,
            "waste_pct": statistics.mean(s.waste_pct for s in rows),
            "lb_gap_mean": lb_mean,
            "lb_gap_max": lb_max,
            "best_gap_mean": best_mean,
            "best_gap_max": best_max,
            "proven_pct": 100 * sum(s.proven for s in rows) / len(rows),
            "opt_gap_mean": opt_mean,
            "opt_gap_max": opt_max,
            "at_optimum_pct": 100 * sum(g < 1e-9 for g in gaps) / len(gaps) if gaps else float("nan"),
            "violating_pct": 100 * sum(bool(s.violations) for s in rows) / len(rows),
            "smell_pct": 100 * sum(bool(s.smells) for s in rows) / len(rows),
            "ms_p50": statistics.median(ms),
            "ms_max": max(ms),
            "ref_s_max": max(s.ref_ms for s in rows) / 1000,
        }
    return out


# ── CLI ──────────────────────────────────────────────────────────

COLS = ["n", "pieces", "purchased_m", "lb_gap_mean", "lb_gap_max", "best_gap_mean",
        "best_gap_max", "proven_pct", "opt_gap_mean", "at_optimum_pct", "violating_pct",
        "smell_pct", "ms_p50", "ms_max", "ref_s_max"]
DELTA_COLS = ["purchased_m", "lb_gap_mean", "lb_gap_max", "best_gap_mean", "proven_pct",
              "violating_pct", "ms_max"]


def _table(rows: dict[str, dict], cols: list[str], first: str = "family") -> None:
    w = max([len(first)] + [len(k) for k in rows]) + 2
    print(f"{first:<{w}}" + "".join(f"{c:>15}" for c in cols))
    for k, m in rows.items():
        cells = "".join(f"{m.get(c, float('nan')):>15.2f}" if isinstance(m.get(c), (int, float))
                        else f"{str(m.get(c, '-')):>15}" for c in cols)
        print(f"{k:<{w}}{cells}")


def _projects_table(scores: list[Score]) -> None:
    rows = {}
    for s in scores:
        if not s.family.startswith("project:"):
            continue
        r = {"ours_m": s.purchased_mm / 1000,
             "lb_m": s.lb_mm / 1000 if s.lb_mm is not None else None,
             "best_m": s.best_mm / 1000 if s.best_mm is not None else None,
             "gap_lb%": s.gap_lb_pct, "proven": str(s.proven),
             "competitor_m": s.competitor_mm / 1000 if s.competitor_mm is not None else None}
        if s.competitor_mm is not None:
            r["ours-comp_m"] = (s.purchased_mm - s.competitor_mm) / 1000
            r["comp_gap_lb%"] = _gap(s.competitor_mm, s.lb_mm)
        rows[s.family.removeprefix("project:")] = {k: v for k, v in r.items() if v is not None}
    if rows:
        print("\nprojects (ours vs competitor vs lower bound)")
        _table(rows, ["ours_m", "competitor_m", "ours-comp_m", "lb_m", "best_m", "gap_lb%",
                      "comp_gap_lb%", "proven"], "project")
        for k, r in rows.items():
            if r.get("comp_gap_lb%", 0) < -1e-6:
                print(f"  WARNING {k}: competitor is below the proven lower bound, so it solved a "
                      "different problem (kerf, stock lengths, client stock, trim?)")


def compare(new: dict, old: dict) -> None:
    print("\ndelta vs baseline (new - old)")
    rows = {}
    for fam, m in new.items():
        o = old.get(fam)
        if o:
            rows[fam] = {c: m[c] - o[c] for c in DELTA_COLS if c in m and c in o}
    _table(rows, DELTA_COLS)


def main(argv: list[str] | None = None) -> None:
    from tekla_nest.config.app_config import load_config

    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="small",
                    choices=["small", "medium", "full", "projects", "all"])
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--kerf", type=float, default=0.0,
                    help="mm per cut (realistic families carry their own 3-5 mm)")
    ap.add_argument("--trim", type=float, default=0.0, help="mm scrapped per bar (e.g. 100)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--time-limit", type=float, default=10.0, help="MILP seconds per group")
    ap.add_argument("--no-reference", action="store_true", help="engine only, no scipy")
    ap.add_argument("--json", help="write machine-readable results here")
    ap.add_argument("--compare", help="baseline JSON from an earlier --json run")
    ap.add_argument("-v", action="store_true", help="list each violation and smell")
    a = ap.parse_args(argv)
    load_config(a.config)
    scores = [run(i, a.kerf, a.trim, not a.no_reference, a.time_limit)
              for i in make_suite(a.suite, a.seeds)]
    fams = summarize(scores)
    print(f"suite={a.suite} seeds={a.seeds} kerf={a.kerf} trim={a.trim} "
          f"hot={get_config().hot_rolled_lengths} other={get_config().other_lengths}")
    _table(fams, COLS)
    _projects_table(scores)
    if a.v:
        for s in scores:
            for msg in s.violations:
                print(f"  VIOLATION {s.name}: {msg}")
            for msg in s.smells:
                print(f"  smell {s.name}: {msg}")
    if a.compare:
        with open(a.compare) as f:
            compare(fams, json.load(f)["families"])
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"args": vars(a), "families": fams,
                       "instances": [asdict(s) for s in scores]}, f, indent=1)


if __name__ == "__main__":
    main()

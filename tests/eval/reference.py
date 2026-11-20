"""Reference solver for the multiple-stock-length cutting stock problem.

Dev-only (scipy/HiGHS). Nothing under src/ may import this.

Problem (one (profile, material) group):
    piece types (length l_i, demand d_i), kerf k between cuts on a bar
    (n cuts use sum(l) + k*(n-1) <= capacity), stock types
    (capacity C_j, cost c_j, optional bound u_j). Market bars cost their
    nominal length; client bars are free but limited. Minimise purchased mm.

Kerf trick: add k to every piece and every capacity, then it is plain
knapsack feasibility: sum(l_i + k) <= C_j + k.

Outputs
- ``lb``: valid lower bound on purchased mm (Lagrangian bound from column
  generation, rounded up to the gcd of market costs).
- ``best``: best integer solution found (MILP over the generated patterns,
  or over ALL maximal patterns when that set is small -> exact).
- ``proven``: best == lb, or the exhaustive MILP finished optimal.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from functools import reduce

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp


@dataclass
class StockType:
    capacity: float  # usable mm (nominal - trim)
    cost: float  # purchased mm (nominal for market, 0 for client)
    bound: int | None = None  # max bars; None = unlimited


@dataclass
class RefResult:
    lb: float
    best: float | None  # None if no integer solution found
    proven: bool
    exact_milp: bool  # solved over all maximal patterns
    cg_iters: int
    n_patterns: int
    ms: float


def _scale(values: list[float]) -> int:
    for s in (1, 10, 100, 1000):
        if all(abs(v * s - round(v * s)) < 1e-6 for v in values):
            return s
    raise ValueError("lengths need more than 3 decimals")


class _Knapsack:
    """Bounded knapsack over all capacities at once (0/1 after binary split)."""

    def __init__(self, weights: list[int], demand: list[int], cmax: int):
        self.items: list[tuple[int, int, int]] = []  # (type, count, weight)
        for i, (w, d) in enumerate(zip(weights, demand, strict=True)):
            n, k = min(d, cmax // w), 1
            while n > 0:
                t = min(k, n)
                self.items.append((i, t, w * t))
                n -= t
                k *= 2
        self.cmax = cmax
        self.ntypes = len(weights)

    def solve(self, values: np.ndarray):
        dp = np.zeros(self.cmax + 1)
        keep = []
        for i, t, w in self.items:
            if values[i] <= 1e-12:
                keep.append(None)
                continue
            cand = dp[:-w] + values[i] * t
            take = np.zeros(self.cmax + 1, dtype=bool)
            take[w:] = cand > dp[w:] + 1e-9
            dp[w:] = np.maximum(dp[w:], cand)
            keep.append(take)
        return dp, keep

    def pattern(self, keep, cap: int) -> tuple[int, ...]:
        a = [0] * self.ntypes
        for (i, t, w), take in zip(reversed(self.items), reversed(keep), strict=True):
            if take is not None and take[cap]:
                a[i] += t
                cap -= w
        return tuple(a)


def _maximal_patterns(weights, demand, cap, limit):
    """All maximal patterns for one capacity; None if more than ``limit``."""
    out: list[tuple[int, ...]] = []
    n = len(weights)
    wmin = min(weights)
    a = [0] * n
    visits = [0]

    def rec(i, room):
        visits[0] += 1
        if len(out) > limit or visits[0] > 50 * limit:
            return
        if i == n:
            # maximal: no type with spare demand still fits
            if all(a[j] >= demand[j] or weights[j] > room for j in range(n)) and any(a):
                out.append(tuple(a))
            return
        for c in range(min(demand[i], room // weights[i]), -1, -1):
            a[i] = c
            rec(i + 1, room - c * weights[i])
        a[i] = 0

    if cap >= wmin:
        rec(0, cap)
    return None if len(out) > limit or visits[0] > 50 * limit else out


def solve(
    lengths: list[float],
    demand: list[int],
    stock: list[StockType],
    kerf: float = 0.0,
    time_limit: float = 10.0,
    max_iters: int = 500,
    exact_limit: int = 3000,
) -> RefResult:
    t0 = time.perf_counter()
    s = _scale(list(lengths) + [kerf])
    w = [round((L + kerf) * s) for L in lengths]
    caps = [int(math.floor((st.capacity + kerf) * s + 1e-6)) for st in stock]
    m, J = len(w), len(stock)
    if any(wi > max(caps) for wi in w):
        raise ValueError("piece longer than every stock bar: filter unfit pieces first")
    d = np.array(demand, dtype=float)
    cost = np.array([st.cost for st in stock])
    bounded = [j for j, st in enumerate(stock) if st.bound is not None]
    big_m = 10 * max(cost.max(), 1.0)
    market = [int(round(c)) for c in cost if c > 0]
    g = reduce(math.gcd, market) if market else 1

    cols: list[tuple[int, tuple[int, ...]]] = []  # (stock j, counts)
    seen = set()

    def add(j, a):
        if (j, a) not in seen and any(a):
            seen.add((j, a))
            cols.append((j, a))

    for i in range(m):  # homogeneous start columns
        for j in range(J):
            k = min(demand[i], caps[j] // w[i])
            if k:
                add(j, tuple(k if t == i else 0 for t in range(m)))

    # Exhaustive maximal patterns when small -> exact MILP.
    exact = []
    for j in range(J):
        pats = _maximal_patterns(w, demand, caps[j], exact_limit)
        if pats is None or len(exact) + len(pats) > exact_limit:
            exact = None
            break
        exact += [(j, a) for a in pats]

    ks = _Knapsack(w, demand, max(caps))
    n_lag = np.array([stock[j].bound if stock[j].bound is not None else sum(demand)
                      for j in range(J)], dtype=float)
    lb, iters = 0.0, 0
    for iters in range(1, max_iters + 1):  # noqa: B007
        A, c, B = _matrix(cols, m, cost, bounded)
        # min c x  s.t.  A x >= d, B x <= u; one big-M slack per demand row
        res = linprog(np.concatenate([c, np.full(m, big_m)]),
                      A_ub=np.vstack([-A, B]),
                      b_ub=np.concatenate([-d, [stock[j].bound for j in bounded]]),
                      bounds=(0, None), method="highs")
        if res.status != 0:
            raise RuntimeError(f"master LP failed: {res.message}")
        duals = -res.ineqlin.marginals
        pi = np.maximum(duals[:m], 0.0)
        sigma = np.zeros(J)
        for r, j in enumerate(bounded):
            sigma[j] = max(duals[m + r], 0.0)
        dp, keep = ks.solve(pi)
        rc = np.array([cost[j] + sigma[j] - dp[caps[j]] for j in range(J)])
        lag = pi @ d - sum(sigma[j] * stock[j].bound for j in bounded) + n_lag @ np.minimum(rc, 0)
        lb = max(lb, lag)
        new = [j for j in range(J) if rc[j] < -1e-7 * max(cost.max(), 1)]
        if not new:
            break
        for j in new:
            add(j, ks.pattern(keep, caps[j]))
    lb = max(lb, 0.0)
    lb_r = math.ceil(lb / g - 1e-6) * g if market else 0.0

    use = exact if exact is not None else cols
    best, exact_done = _milp(use, m, cost, d, stock, bounded, big_m,
                             time_limit - (time.perf_counter() - t0))
    proven = best is not None and (best <= lb_r + 1e-6 or (exact is not None and exact_done))
    if proven and exact is not None and exact_done:
        lb_r = max(lb_r, best)  # exhaustive optimum is itself the bound
    return RefResult(lb=lb_r, best=best, proven=proven, exact_milp=exact is not None and exact_done,
                     cg_iters=iters, n_patterns=len(use), ms=(time.perf_counter() - t0) * 1000)


def _matrix(cols, m, cost, bounded):
    """Demand matrix [patterns | slack identity], cost, bound-row matrix."""
    n = len(cols)
    A = np.zeros((m, n + m))
    B = np.zeros((len(bounded), n + m))
    row = {j: r for r, j in enumerate(bounded)}
    for p, (j, a) in enumerate(cols):
        A[:, p] = a
        if j in row:
            B[row[j], p] = 1.0
    A[:, n:] = np.eye(m)
    return A, np.array([cost[j] for j, _ in cols]), B


def _milp(cols, m, cost, d, stock, bounded, big_m, time_limit):
    A, c, B = _matrix(cols, m, cost, bounded)
    n = len(cols)
    cons = [LinearConstraint(A, lb=d, ub=np.inf)]
    if bounded:
        cons.append(LinearConstraint(B, lb=0, ub=[stock[j].bound for j in bounded]))
    res = milp(np.concatenate([c, np.full(m, big_m)]), constraints=cons,
               integrality=np.ones(n + m), bounds=Bounds(0, np.inf),
               options={"time_limit": max(time_limit, 1.0), "disp": False})
    if res.x is None:
        return None, False
    x = np.round(res.x)
    if x[n:].any():  # slack used: demand cannot be met with this stock
        return None, False
    return float(c @ x[:n]), res.status == 0


if __name__ == "__main__":
    # self-check: 3 x 6000 on {6100, 12100, 16100} -> 12100 + 6100
    st = [StockType(L, L) for L in (6100, 12100, 16100)]
    r = solve([6000], [3], st)
    assert r.best == 18200 and r.proven and r.lb == 18200, r
    # kerf 5: 2 x 6050 no longer fit 12100
    r = solve([6050], [2], [StockType(L, L) for L in (6100, 12100)], kerf=5)
    assert r.best == 12200, r
    # free client bar of 6000 takes one piece
    r = solve([6000], [3], st + [StockType(6000, 0, 1)])
    assert r.best == 12100 and r.proven, r
    print("ok")

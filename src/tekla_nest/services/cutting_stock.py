"""Multiple-stock-size 1D cutting stock solver (pure Python, stdlib only).

Works on piece TYPES, not individual pieces: ``widths[t]`` is a piece length
plus one kerf, ``demand[t]`` how many are needed. A stock type has
``cap = length + kerf``; a pattern ``a`` fits it iff
``sum(a[t] * widths[t]) <= cap`` -- exactly "kerf only between cuts".

Objective, lexicographic: fewest unfit pieces, least purchase cost (market
length; client stock is free), fewest bars, lowest priority sum, least stock
length, least scrap, biggest reusable offcuts.

Portfolio (the best plan wins):

1. Gilmore-Gomory column generation: dense revised-simplex master LP,
   bounded-knapsack branch-and-bound pricing per stock type. Its optimum is
   a valid lower bound on purchased length (``CuttingStock.lower_bound``).
2. Residual rounding: fix ``floor(x)`` of the LP columns, re-solve the LP on
   what is left, round the largest column up when nothing is integral; small
   residuals are finished exactly.
3. Exact solver: enumerate stock-length multisets in objective order and
   prove/deny each one with a memoised bin-packing DFS. Runs on the whole
   instance when it is small, on residuals, and as a local search that
   re-optimises 2-3 bars at a time.

Every search is node-budgeted, never wall-clock limited, so the same input
always yields the same plan.
"""
from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from itertools import combinations

EPS = 1e-6
ROOT_ITERS = 4000          # root CG pivot budget

# Node budgets (deterministic work limits). Sized so 500 pieces stay < 1 s.
EXACT_ITEMS = 40          # run the whole-instance exact search up to this many pieces
EXACT_NODES = 150_000     # DFS nodes for the whole-instance exact search
RESIDUAL_ITEMS = 16       # finish a rounding residual exactly below this size
LOCAL_NODES = 150_000     # DFS nodes for the 2-3 bar local search
KNAP_NODES = 30_000       # per exhaustive pricing knapsack
QUICK_NODES = 300         # per heuristic pricing knapsack (tried first)
MAX_COMBOS = 20_000       # stock multisets per exact call


@dataclass(frozen=True)
class Stock:
    """One stock type (a group of identical physical bars)."""

    cap: float      # length + kerf
    cost: float     # purchase cost: length for market stock, 0 for client stock
    qty: int
    prio: int
    length: float


Pattern = tuple[int, ...]
Bar = tuple[int, Pattern]  # (stock index, pieces per type)


class _Budget(Exception):
    """A deterministic node budget ran out."""


class CuttingStock:
    """Solver for one (profile, material) group.

    ``widths`` must be sorted descending. ``stocks`` should be sorted by
    preference ``(cost, prio, cap)``: restocking takes the first that fits.
    """

    def __init__(
        self,
        widths: list[float],
        demand: list[int],
        stocks: list[Stock],
        scrap_threshold: float = 0.0,
    ) -> None:
        self.w = widths
        self.d = demand
        self.T = len(widths)
        self.stocks = stocks
        self.S = len(stocks)
        self.thr = scrap_threshold
        self.lower_bound: float | None = None  # LP bound on purchase cost
        self.proven_optimal = False

    # ── Plan helpers ─────────────────────────────────────────

    def need(self, pat: Pattern) -> float:
        return sum(a * w for a, w in zip(pat, self.w, strict=True) if a)

    def key(self, bars: list[Bar], unfit: int) -> tuple:
        st = self.stocks
        rems = [st[j].cap - self.need(p) for j, p in bars]
        return (
            unfit,
            round(sum(st[j].cost for j, _ in bars), 6),
            len(bars),
            sum(st[j].prio for j, _ in bars),
            round(sum(st[j].length for j, _ in bars), 6),
            round(sum(r for r in rems if r <= self.thr), 6),
            -round(sum(r * r for r in rems if r > self.thr), 3),
        )

    def restock(
        self, pats: list[Pattern], avail: list[int] | None = None
    ) -> tuple[list[Bar], list[int]]:
        """Give every pattern its cheapest stock; returns (bars, unfit counts).

        Bars are served largest need first; each takes the first stock type
        (preference order) that fits. Feasible sets are nested by need, so this
        never fails when an assignment exists, and it hands free client bars
        to the bars whose market replacement would cost the most.
        """
        avail = list(avail if avail is not None else [s.qty for s in self.stocks])
        needs = [self.need(p) for p in pats]
        bars: list[Bar] = []
        unfit = [0] * self.T
        for i in sorted(range(len(pats)), key=lambda i: (-needs[i], i)):
            j = next(
                (j for j, s in enumerate(self.stocks)
                 if avail[j] > 0 and s.cap + EPS >= needs[i]),
                None,
            )
            if j is None:
                unfit = [u + a for u, a in zip(unfit, pats[i], strict=True)]
                continue
            avail[j] -= 1
            bars.append((j, pats[i]))
        return bars, unfit

    # ── Top level ────────────────────────────────────────────

    def solve(self, seeds: list[list[Pattern]]) -> tuple[list[Bar], list[int]]:
        """Return the best plan (bars, unfit counts per type)."""
        best: tuple | None = None
        best_plan: tuple[list[Bar], list[int]] = ([], list(self.d))

        def offer(bars: list[Bar], _unfit: object = None) -> None:
            nonlocal best, best_plan
            unfit = list(self.d)
            for _, p in bars:
                unfit = [u - a for u, a in zip(unfit, p, strict=True)]
            k = self.key(bars, sum(unfit))
            if best is None or k < best:
                best, best_plan = k, (bars, unfit)

        pool: list[Bar] = []
        for pats in seeds:
            bars, unfit = self.restock(pats)
            offer(bars, unfit)
            pool.extend(bars)

        n_items = sum(self.d)
        qty = [s.qty for s in self.stocks]
        x, lb, art = self.lp(self.d, qty, pool, max_iter=ROOT_ITERS)
        self.lower_bound = lb
        lb_round = self._purchasable(lb) if lb is not None else 0.0

        def done() -> bool:
            return best is not None and best[0] == 0 and best[1] <= lb_round + EPS

        if not done():
            offer(*self.dive(pool, x))
        if not done() and art < EPS:
            offer(*self.improve(best_plan[0], best_plan[1]))
        if not done() and art < EPS and n_items <= EXACT_ITEMS:
            budget = [EXACT_NODES]
            ub = best[1:5] if best is not None and best[0] == 0 else (math.inf,)
            bars = self.exact(list(self.d), qty, ub, budget, lb_cost=lb_round)
            if bars is not None:
                offer(bars, [0] * self.T)
                self.proven_optimal = True
            elif budget[0] > 0:
                # Search finished without beating the incumbent: it is optimal.
                self.proven_optimal = best is not None and best[0] == 0
        if done():
            self.proven_optimal = True
        return best_plan

    # ── Column generation LP ─────────────────────────────────

    def lp(
        self, d: list[int], avail: list[int], pool: list[Bar], max_iter: int = 4000,
        exact: bool = True,
    ) -> tuple[list[tuple[Bar, float]], float | None, float]:
        """Solve the master LP over ``pool`` plus generated columns.

        Returns (positive columns with values, purchase-cost bound or None,
        artificial (= unplaceable) LP mass). ``pool`` gets the new columns.
        """
        st = self.stocks
        rows = [t for t in range(self.T) if d[t] > 0]
        if not rows:
            return [], 0.0, 0.0
        row_of = {t: r for r, t in enumerate(rows)}
        total = sum(d[t] * self.w[t] for t in rows)
        usable = [j for j in range(self.S) if avail[j] > 0]
        lim = [j for j in usable if avail[j] * st[j].cap < total + EPS]
        lim_row = {j: len(rows) + q for q, j in enumerate(lim)}
        R = len(rows) + len(lim)
        big_m = 2.0 * max([st[j].cost for j in usable] + [1.0]) + 1.0
        tol = 1e-9 * big_m

        cost: list[float] = []
        ent: list[list[tuple[int, float]]] = []
        cols: list[Bar | None] = []
        seen: dict[Bar, int] = {}
        for r in range(len(rows)):  # artificials (= unfit), then surplus
            cost.append(big_m), ent.append([(r, 1.0)]), cols.append(None)
        for r in range(len(rows)):
            cost.append(0.0), ent.append([(r, -1.0)]), cols.append(None)
        for j in lim:
            cost.append(0.0), ent.append([(lim_row[j], 1.0)]), cols.append(None)
        # Dual-optimal inequalities y[t] >= y[t+1] (Valerio de Carvalho): a
        # longer piece may stand in for a shorter one. Same LP optimum, far
        # fewer degenerate column-generation iterations.
        for r in range(len(rows) - 1):
            cost.append(0.0), ent.append([(r, -1.0), (r + 1, 1.0)]), cols.append(None)

        def add(j: int, pat: Pattern) -> int | None:
            pat = tuple(min(a, d[t]) for t, a in enumerate(pat))
            if (j, pat) in seen:
                return seen[(j, pat)]
            if not any(pat) or avail[j] <= 0 or self.need(pat) > st[j].cap + EPS:
                return None
            e = [(row_of[t], float(a)) for t, a in enumerate(pat) if a]
            if j in lim_row:
                e.append((lim_row[j], 1.0))
            cost.append(st[j].cost), ent.append(e), cols.append((j, pat))
            seen[(j, pat)] = len(cost) - 1
            return len(cost) - 1

        for j, pat in pool:
            add(j, pat)

        basis = list(range(len(rows))) + list(range(2 * len(rows), 2 * len(rows) + len(lim)))
        in_basis = set(basis)
        binv = [[1.0 if c == r else 0.0 for c in range(R)] for r in range(R)]
        rhs = {t: float(d[t]) for t in rows}
        xb = [rhs[t] for t in rows] + [float(avail[j]) for j in lim]
        # Crash basis: homogeneous patterns replace the artificials, so the
        # simplex starts feasible and close to optimal. B stays block lower
        # triangular ([[diag, 0], [E, I]]), so its inverse is written directly.
        used = {j: 0.0 for j in lim}
        for r, t in enumerate(rows):
            best_h = None
            for j in usable:
                a = min(d[t], int((st[j].cap + EPS) // self.w[t]))
                if a <= 0 or (j in used and used[j] + rhs[t] / a > avail[j] + EPS):
                    continue
                h = (st[j].cost / a, j, a)
                best_h = h if best_h is None or h < best_h else best_h
            if best_h is None:
                continue
            _, j, a = best_h
            c = add(j, tuple(a if u == t else 0 for u in range(self.T)))
            basis[r] = c
            binv[r][r] = 1.0 / a
            xb[r] = rhs[t] / a
            if j in used:
                q = lim_row[j]
                used[j] += rhs[t] / a
                binv[q][r] = -1.0 / a
                xb[q] = max(0.0, xb[q] - rhs[t] / a)
        in_basis = set(basis)
        cb = [cost[c] for c in basis]
        exact_pricing = True
        degenerate = 0
        converged = False
        rot = 0

        for it in range(max_iter):
            if it % 50 == 0:  # y = cB B^-1, refreshed now and then against drift
                y = [0.0] * R
                for k in range(R):
                    if cb[k]:
                        f = cb[k]
                        y = [yi + f * bi for yi, bi in zip(y, binv[k], strict=True)]
            enter, best_rc = -1, -tol
            vals = [y[row_of[t]] if t in row_of else 0.0 for t in range(self.T)]

            def offer(c: int | None) -> None:
                nonlocal enter, best_rc
                if c is not None and c not in in_basis:
                    rc = cost[c] - sum(y[r] * a for r, a in ent[c])  # noqa: B023
                    if rc < best_rc:
                        enter, best_rc = c, rc

            # 1. cheap pricing: a few hundred knapsack nodes per stock type
            # (partial pricing: stock types round-robin, stop at the first hit)
            hard = []
            for q in range(len(usable)):
                j = usable[(rot + q) % len(usable)]
                thr = st[j].cost - (y[lim_row[j]] if j in lim_row else 0.0)
                pat, ok = self._knapsack(vals, d, st[j].cap, thr, tol, QUICK_NODES)
                if pat is not None:
                    offer(add(j, pat))
                    if enter >= 0:
                        rot = (rot + q + 1) % len(usable)
                        break
                elif not ok:
                    hard.append((j, thr))
            # 2. every known column (slacks, surplus, old patterns)
            if enter < 0:
                bland = degenerate > 50
                for c in range(len(cost)):
                    offer(c)
                    if bland and enter >= 0:
                        break
            # 3. exhaustive pricing, only to prove LP optimality
            if enter < 0:
                for j, thr in hard:
                    if not exact:
                        exact_pricing = False
                        break
                    pat, ok = self._knapsack(vals, d, st[j].cap, thr, tol)
                    exact_pricing &= ok
                    if pat is not None:
                        offer(add(j, pat))
                        if enter >= 0:
                            break
            if enter < 0:
                converged = True
                break
            a = ent[enter]
            dcol = [sum(row[r] * v for r, v in a) for row in binv]
            p, theta = -1, math.inf
            for k in range(R):
                if dcol[k] > 1e-9:
                    ratio = xb[k] / dcol[k]
                    if ratio < theta - 1e-12 or (
                        ratio <= theta + 1e-12 and basis[k] < basis[p]
                    ):
                        p, theta = k, ratio
            if p < 0:
                break  # unbounded: impossible with costs >= 0
            degenerate = degenerate + 1 if theta < 1e-9 else 0
            piv = dcol[p]
            rowp = [v / piv for v in binv[p]]
            binv[p] = rowp
            xp = xb[p] / piv
            for k in range(R):
                f = dcol[k]
                if k != p and f:
                    binv[k] = [u - f * v for u, v in zip(binv[k], rowp, strict=True)]
                    xb[k] = max(0.0, xb[k] - f * xp)
            xb[p] = xp
            in_basis.discard(basis[p])
            basis[p] = enter
            in_basis.add(enter)
            cb[p] = cost[enter]
            y = [yi + best_rc * bi for yi, bi in zip(y, rowp, strict=True)]  # O(R) dual update

        art = sum(xb[k] for k in range(R) if basis[k] < len(rows))
        x = [(cols[basis[k]], xb[k]) for k in range(R)
             if cols[basis[k]] is not None and xb[k] > EPS]
        pool[:] = [c for c in cols if c is not None]
        lb = None
        if converged and exact_pricing and art < EPS:
            lb = sum(st[b[0]].cost * v for b, v in x)
        elif exact and art < EPS and all(st[j].cost > 0 for j in usable):
            lb = self._farley(y, rows, row_of, d, usable, tol)
        return x, lb, art

    def _farley(self, y, rows, row_of, d, usable, tol) -> float | None:
        """Farley bound for a not fully converged LP: with duals pi >= 0 and
        r = max_j best_pattern_value_j / cost_j, every plan costs >= pi.d / r
        (stock limits are relaxed, which keeps it a valid lower bound)."""
        pi = [max(0.0, y[row_of[t]]) if t in row_of else 0.0 for t in range(self.T)]
        r = 0.0
        for j in usable:
            pat, ok = self._knapsack(pi, d, self.stocks[j].cap, 0.0, tol, 20 * KNAP_NODES)
            if not ok:
                return None
            if pat is not None:
                r = max(r, sum(p * a for p, a in zip(pi, pat, strict=True)) / self.stocks[j].cost)
        return sum(pi[t] * d[t] for t in rows) / r if r > 0 else None

    def _knapsack(
        self, vals: list[float], ub: list[int], cap: float, thr: float, tol: float,
        max_nodes: int = KNAP_NODES,
    ) -> tuple[Pattern | None, bool]:
        """Bounded knapsack B&B: max sum(vals*a), sum(w*a) <= cap, a <= ub.

        Returns (pattern with value > thr or None, search completed).
        """
        idx = [t for t in range(self.T)
               if ub[t] > 0 and vals[t] > tol and self.w[t] <= cap + EPS]
        idx.sort(key=lambda t: (-vals[t] / self.w[t], t))
        V = [vals[t] for t in idx]
        W = [self.w[t] for t in idx]
        U = [ub[t] for t in idx]
        n = len(idx)
        best_val, best = thr + tol, None
        cur = [0] * n
        nodes = 0

        cw = [0.0] * (n + 1)  # prefix sums for an O(log n) Dantzig bound
        cv = [0.0] * (n + 1)
        for i in range(n):
            cw[i + 1] = cw[i] + U[i] * W[i]
            cv[i + 1] = cv[i] + U[i] * V[i]

        def dfs(k: int, room: float, val: float) -> None:
            nonlocal best_val, best, nodes
            if val > best_val:
                best_val, best = val, cur[:]
            if k == n:
                return
            nodes += 1
            if nodes > max_nodes:
                raise _Budget
            k1 = k + 1
            c = min(U[k], int((room + EPS) // W[k]))
            while c >= 0:
                r = room - c * W[k]
                v = val + c * V[k]
                # Dantzig bound of the child; it only shrinks as c drops
                # (items after k have a lower value/width ratio), so stop.
                i = max(k1, bisect_right(cw, cw[k1] + r, k1) - 1)
                bd = cv[i] - cv[k1]
                if i < n:
                    bd += V[i] * (r - (cw[i] - cw[k1])) / W[i]
                if v + bd <= best_val + tol:
                    break
                cur[k] = c
                dfs(k1, r, v)
                c -= 1
            cur[k] = 0

        ok = True
        try:
            dfs(0, cap, 0.0)
        except _Budget:
            ok = False
        if best is None:
            return None, ok
        pat = [0] * self.T
        for i, t in enumerate(idx):
            pat[t] = best[i]
        return tuple(pat), ok

    def _purchasable(self, z: float) -> float:
        """Smallest sum of market lengths >= z (still a valid lower bound)."""
        market = sorted({s.length for s in self.stocks if s.cost > 0})
        if z <= EPS or not market or not all(float(L).is_integer() for L in market):
            return max(z, 0.0)
        ints = [int(L) for L in market]
        g = math.gcd(*ints)
        t = math.ceil((z - 1e-6) / g)
        sc = [L // g for L in ints]
        if t > 200_000:
            return float(t * g)
        reach = bytearray(t + max(sc) + 1)
        reach[0] = 1
        for v in range(1, len(reach)):
            if any(v >= s and reach[v - s] for s in sc):
                reach[v] = 1
                if v >= t:
                    return float(v * g)
        return float(t * g)

    # ── Residual rounding ────────────────────────────────────

    def dive(
        self, pool: list[Bar], x: list[tuple[Bar, float]]
    ) -> tuple[list[Bar], list[int]]:
        d = list(self.d)
        avail = [s.qty for s in self.stocks]
        pats: list[Pattern] = []

        def apply(j: int, pat: Pattern) -> bool:
            clipped = tuple(min(a, r) for a, r in zip(pat, d, strict=True))
            if avail[j] <= 0 or not any(clipped):
                return False
            avail[j] -= 1
            for t, a in enumerate(clipped):
                d[t] -= a
            pats.append(clipped)
            return True

        for it in range(10 * self.T + 10):
            left = sum(d)
            if not left:
                break
            if left <= RESIDUAL_ITEMS:
                break
            if it:
                x, _, _ = self.lp(d, avail, pool, max_iter=1000, exact=False)
            x = sorted(x, key=lambda bv: -bv[1])
            moved = False
            for (j, pat), v in x:
                for _ in range(int(v + 1e-6)):
                    moved |= apply(j, pat)
            if not moved and not any(apply(j, pat) for (j, pat), _ in x[:1]):
                break
        # finish: greedy, then exact if the residual is small
        fb, funfit = self._ffd(d, avail)
        if sum(d) <= RESIDUAL_ITEMS and not sum(funfit):
            ub = self.key(fb, 0)[1:5]
            ex = self.exact(d, avail, ub, [LOCAL_NODES // 3])
            if ex is not None:
                fb = ex
        bars, unfit = self.restock(pats + [p for _, p in fb])
        unfit = [u + f for u, f in zip(unfit, funfit, strict=True)]
        return bars, unfit

    def _ffd(self, d: list[int], avail: list[int]) -> tuple[list[Bar], list[int]]:
        """First-fit decreasing; new bars take the longest stock still available."""
        avail = list(avail)
        open_bars: list[list] = []  # [j, room, counts]
        unfit = [0] * self.T
        for t in range(self.T):
            for _ in range(d[t]):
                w = self.w[t]
                bar = next((b for b in open_bars if b[1] + EPS >= w), None)
                if bar is None:
                    j = max((j for j in range(self.S) if avail[j] > 0),
                            key=lambda j: (self.stocks[j].cap, -j), default=None)
                    if j is None or self.stocks[j].cap + EPS < w:
                        unfit[t] += 1
                        continue
                    avail[j] -= 1
                    bar = [j, self.stocks[j].cap, [0] * self.T]
                    open_bars.append(bar)
                bar[1] -= w
                bar[2][t] += 1
        return [(b[0], tuple(b[2])) for b in open_bars], unfit

    # ── Exact search ─────────────────────────────────────────

    def exact(
        self,
        cnt: list[int],
        avail: list[int],
        ub: tuple,
        budget: list[int],
        lb_cost: float = 0.0,
        max_bins: int | None = None,
    ) -> list[Bar] | None:
        """Best plan for exactly ``cnt`` pieces whose (cost, bars, prio,
        length) key is < ``ub``; None if there is none or budget ran out."""
        types = [t for t in range(self.T) for _ in range(cnt[t])]
        if not types:
            return []
        items = [self.w[t] for t in types]
        tot, big, small = sum(items), items[0], items[-1]
        st = self.stocks
        js = [j for j in range(self.S) if avail[j] > 0 and st[j].cap + EPS >= small]
        max_bins = min(max_bins or len(items), len(items))
        combos: list[tuple[tuple, tuple[int, ...]]] = []
        cur: list[int] = []
        ub_cost = ub[0]

        def rec(pos: int, cost: float, n: int, prio: int, caps: float,
                length: float, maxcap: float) -> None:
            if pos == len(js):
                if n and caps + EPS >= tot and maxcap + EPS >= big and cost + EPS >= lb_cost:
                    k = (round(cost, 6), n, prio, round(length, 6))
                    if k < ub:
                        combos.append((k, tuple(cur)))
                        if len(combos) > MAX_COMBOS:
                            raise _Budget
                return
            j = js[pos]
            s = st[j]
            for c in range(min(avail[j], max_bins - n) + 1):
                if cost + c * s.cost > ub_cost + EPS:
                    break
                cur.extend([j] * c)
                rec(pos + 1, cost + c * s.cost, n + c, prio + c * s.prio,
                    caps + c * s.cap, length + c * s.length,
                    max(maxcap, s.cap) if c else maxcap)
                if c:
                    del cur[-c:]

        try:
            rec(0, 0.0, 0, 0, 0.0, 0.0, 0.0)
            combos.sort()
            cache: dict[tuple[float, ...], list[int] | None] = {}
            for _, combo in combos:
                bins = sorted(combo, key=lambda j: (-st[j].cap, j))
                sig = tuple(st[j].cap for j in bins)
                if sig not in cache:
                    cache[sig] = self._pack(items, list(sig), budget)
                where = cache[sig]
                if where is None:
                    continue
                out = [[0] * self.T for _ in bins]
                for i, b in enumerate(where):
                    out[b][types[i]] += 1
                return [(j, tuple(p)) for j, p in zip(bins, out, strict=True) if any(p)]
        except _Budget:
            budget[0] = min(budget[0], 0)
            return None
        return None

    def _pack(self, items: list[float], caps: list[float], budget: list[int]) -> list[int] | None:
        """Bin-packing feasibility DFS: items (descending) into bins ``caps``."""
        n, m = len(items), len(caps)
        slack = sum(caps) - sum(items)
        if slack < -EPS:
            return None
        smallest = items[-1]
        loads = [0.0] * m
        where = [0] * n
        failed: set = set()

        def dfs(i: int, waste: float) -> bool:
            if i == n:
                return True
            budget[0] -= 1
            if budget[0] < 0:
                raise _Budget
            sig = (i, tuple(sorted(zip(caps, (round(v, 6) for v in loads), strict=True))))
            if sig in failed:
                return False
            w = items[i]
            cand: list[tuple[float, int]] = []
            seen = set()
            for b in range(m):
                free = caps[b] - loads[b]
                if free + EPS < w:
                    continue
                if free - w <= EPS:  # exact fill dominates every other choice
                    cand = [(0.0, b)]
                    break
                s = (caps[b], round(loads[b], 6))
                if s not in seen:
                    seen.add(s)
                    cand.append((free, b))
            cand.sort()  # best fit first
            for _, b in cand:
                after = caps[b] - loads[b] - w
                nw = waste + (after if after + EPS < smallest else 0.0)
                if nw > slack + EPS:
                    continue
                loads[b] += w
                where[i] = b
                if dfs(i + 1, nw):
                    return True
                loads[b] -= w
            failed.add(sig)
            return False

        return where if dfs(0, 0.0) else None

    # ── Local search ─────────────────────────────────────────

    def improve(self, bars: list[Bar], unfit: list[int]) -> tuple[list[Bar], list[int]]:
        """Re-solve groups of 2-3 bars exactly while that lowers the key."""
        bars = list(bars)
        budget = [LOCAL_NODES]
        st = self.stocks
        while budget[0] > 0 and len(bars) > 1:
            spare = [s.qty for s in st]
            for j, _ in bars:
                spare[j] -= 1
            waste = sorted(range(len(bars)),
                           key=lambda i: (-(st[bars[i][0]].cap - self.need(bars[i][1])), i))
            top = waste[:10]
            needs = [self.need(p) for _, p in bars]
            max_cap = max(s.cap for s in st)
            # pairs that fit one bar (merge), pairs with the worst bars,
            # then triples of the worst bars
            merges = [(i, j) for i, j in combinations(range(len(bars)), 2)
                      if needs[i] + needs[j] <= max_cap + EPS]
            groups = merges + [(i, j) for i in top for j in range(len(bars)) if j != i]
            groups += list(combinations(sorted(waste[:7]), 3))
            changed = False
            for g in groups:
                cnt = [sum(bars[i][1][t] for i in g) for t in range(self.T)]
                av = list(spare)
                for i in g:
                    av[bars[i][0]] += 1
                gb = [bars[i] for i in g]
                ub = (round(sum(st[j].cost for j, _ in gb), 6), len(gb),
                      sum(st[j].prio for j, _ in gb),
                      round(sum(st[j].length for j, _ in gb), 6))
                new = self.exact(cnt, av, ub, budget, max_bins=len(g) + 1)
                if budget[0] <= 0:
                    break
                if new is not None:
                    bars = [b for i, b in enumerate(bars) if i not in g] + new
                    changed = True
                    break
            if not changed:
                break
        return bars, unfit

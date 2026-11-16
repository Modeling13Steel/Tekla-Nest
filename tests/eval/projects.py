"""Realistic Tekla-style project generators + real project fixture loader.

Generators are seeded and deterministic. ``size`` scales marks and
quantities: "medium" (fast gate, ~100-300 pieces) or "full" (slow suite,
up to ~1000 pieces per profile and ~3000 per project).

Fixtures: tests/eval/projects/<name>/
    parts.csv      app parts CSV (quantidade;comprimento;referencia;perfil;material)
    stock.csv      optional client stock CSV (quantidade;comprimento;prioridade;perfil;material)
    expected.json  optional, e.g. {"kerf_mm": 3,
                   "competitor": {"purchased_m": 412.3, "bars": 37, "tool": "..."}}
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.services.csv_loader import load_parts_csv, load_stock_csv

PROJECTS_DIR = Path(__file__).parent / "projects"
GRID = [6000, 7500, 8000, 9000]
SIZES = {"medium": 0.3, "full": 1.0}


def _r5(x: float) -> float:
    return float(int(x) // 5 * 5)


class _Job:
    def __init__(self, rng: random.Random, scale: float):
        self.rng, self.scale, self.parts = rng, scale, []

    def qty(self, lo: int, hi: int) -> int:
        return max(1, round(self.rng.randint(lo, hi) * self.scale))

    def marks(self, n: int) -> int:
        return max(1, round(n * max(self.scale, 0.3)))

    def add(self, prefix: str, profile: str, material: str, length: float, q: int) -> None:
        self.parts.append(PartEntry(q, _r5(length), f"{prefix}{len(self.parts) + 1}",
                                    profile, material))

    def offset(self, lo: int = 10, hi: int = 160) -> int:
        """Connection offset at one end (end plate, gap, half column web)."""
        return self.rng.randint(lo, hi) // 5 * 5


def frame(rng: random.Random, scale: float) -> list[PartEntry]:
    """Multi-storey building frame: columns, primary/secondary beams, braces."""
    j = _Job(rng, scale)
    storey = rng.choice([3600, 4000, 4200, 4500])
    for _ in range(j.marks(8)):  # columns, spliced every 1-3 storeys
        n = rng.randint(1, 3)
        j.add("C", rng.choice(["HEB300", "HEB240"]), "S355JR",
              n * storey - j.offset(20, 400), j.qty(2, 40))
    for _ in range(j.marks(24)):  # beams: grid spacing minus both end offsets
        span = rng.choice(GRID)
        j.add("B", rng.choice(["IPE400", "IPE300", "IPE240"]), rng.choice(["S275JR", "S355JR"]),
              span - j.offset() - j.offset(), j.qty(2, 80))
    for _ in range(j.marks(10)):  # vertical bracing on the diagonal
        span = rng.choice(GRID)
        j.add("X", rng.choice(["HEA160", "CHS114.3*4"]), "S275JR",
              math.hypot(span, storey) - 2 * j.offset(50, 250), j.qty(2, 24))
    for _ in range(j.marks(6)):  # edge beams
        j.add("E", "UPN200", "S275JR", rng.choice(GRID) - j.offset(5, 60), j.qty(4, 40))
    return j.parts


def hall(rng: random.Random, scale: float) -> list[PartEntry]:
    """Portal-frame hall: long rafters near stock lengths, a few too long."""
    j = _Job(rng, scale)
    half_span = rng.choice([13000, 14000, 15000, 15500])
    pitch = math.cos(math.radians(rng.choice([5, 6, 8, 10])))
    for _ in range(j.marks(8)):  # rafters 13-16.3 m
        j.add("R", "IPE500", "S355JR", half_span / pitch - j.offset(0, 600) + rng.randint(-200, 300),
              j.qty(4, 30))
    j.add("R", "IPE500", "S355JR", 16300 + rng.randint(0, 400), max(1, round(2 * scale)))  # unfit
    eave = rng.choice([7000, 8000, 9000, 10000])
    for _ in range(j.marks(6)):  # columns
        j.add("C", "HEA450", "S355JR", eave - j.offset(0, 300), j.qty(4, 30))
    bay = rng.choice([6000, 7500])
    for _ in range(j.marks(6)):  # wind bracing (tube, 6000/12000 stock)
        j.add("W", "CHS114.3*4", "S275JR", math.hypot(bay, eave / 2) - j.offset(50, 300),
              j.qty(4, 24))
    for _ in range(j.marks(4)):  # eaves struts / ties
        j.add("T", "SHS100*5", "S275JR", bay - j.offset(5, 80), j.qty(8, 40))
    for _ in range(j.marks(6)):  # haunches / stubs
        j.add("H", "IPE500", "S355JR", rng.randint(600, 2500), j.qty(4, 30))
    return j.parts


def secondary(rng: random.Random, scale: float) -> list[PartEntry]:
    """Secondary steel: hundreds of purlins, girts, cleats (~1000 pcs/profile)."""
    j = _Job(rng, scale)
    for _ in range(j.marks(14)):  # purlins: one span plus lap
        j.add("P", "C200*2.5", "S355JR",
              rng.choice([6000, 7500]) + rng.choice([0, 300, 600]) - j.offset(0, 60),
              j.qty(20, 120))
    for _ in range(j.marks(10)):  # girts
        j.add("G", "C150*2", "S355JR", rng.choice([6000, 7500]) - j.offset(5, 80), j.qty(20, 90))
    for _ in range(j.marks(20)):  # cleats
        j.add("K", "L80*8", "S275JR", rng.randint(150, 400), j.qty(20, 90))
    for _ in range(j.marks(10)):  # trimmers, sag bars
        j.add("S", "FL60*8", "S235JR", rng.randint(400, 2600), j.qty(10, 80))
    return j.parts


def multi(rng: random.Random, scale: float) -> list[PartEntry]:
    """Full project: 10+ (profile, material) groups incl. the same profile in
    two grades, tubes/angles on 6000/12000 (~3000 pieces at full size)."""
    parts = frame(rng, scale) + hall(rng, scale * 0.6) + secondary(rng, scale * 0.6)
    j = _Job(rng, scale)
    for prof, mat in [("IPE300", "S235JR"), ("RHS200*100*6", "S355JR"), ("L100*10", "S275JR"),
                      ("SHS80*4", "S355JR"), ("UPE160", "S275JR"), ("HEM200", "S355JR")]:
        for _ in range(j.marks(5)):
            j.add("M", prof, mat, rng.randint(800, 11000), j.qty(2, 30))
    return parts + j.parts


def client_offcuts(rng: random.Random, parts: list[PartEntry]) -> list[StockEntry]:
    """Yard offcuts with limited quantities for about half of the groups."""
    out = []
    for prof, mat in sorted({(p.profile, p.material) for p in parts}):
        if rng.random() < 0.5:
            for _ in range(rng.randint(1, 4)):
                out.append(StockEntry(rng.randint(1, 6), float(rng.randint(15, 95) * 100),
                                      0, prof, mat, "Cliente"))
    return out


GENERATORS = {"frame": frame, "hall": hall, "secondary": secondary, "multi": multi}


def realistic(size: str, seeds: int):
    """Yield (family, seed, parts, client, kerf) for every realistic family.

    Each generator also has an ``-offcuts`` variant with client stock.
    """
    for seed in range(seeds):
        for fam, gen in GENERATORS.items():
            for offcuts in (False, True):
                name = f"{fam}{'-offcuts' if offcuts else ''}-{size}"
                rng = random.Random(f"{name}-{seed}")
                parts = gen(rng, SIZES[size])
                client = client_offcuts(rng, parts) if offcuts else []
                yield name, seed, parts, client, float(rng.choice([3, 4, 5]))


def load_project(path: Path | str) -> tuple[list[PartEntry], list[StockEntry], dict]:
    """Load a project folder (see module docstring). Needs the app config loaded."""
    path = Path(path)
    parts = load_parts_csv(path / "parts.csv")
    client = load_stock_csv(path / "stock.csv") if (path / "stock.csv").exists() else []
    expected = json.loads((path / "expected.json").read_text()) if (
        path / "expected.json").exists() else {}
    return parts, client, expected


def project_dirs() -> list[Path]:
    return sorted(p for p in PROJECTS_DIR.iterdir() if (p / "parts.csv").exists())

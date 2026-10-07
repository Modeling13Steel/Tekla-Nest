"""Deterministic sample frame for the demo-video capture pipeline."""
from __future__ import annotations

import json
import math
from pathlib import Path

from tekla_nest.providers.tekla_provider import _group_parts

BUILD_DIR = Path(__file__).resolve().parent / "build"
MODEL_PATH = BUILD_DIR / "model.json"
MATERIAL = "S355JR"

_X_SPANS = [6000, 6200, 5800, 6400, 5600]
_Y_SPANS = [6000, 5500, 6500, 6000]
_STOREY_HEIGHT = 4000
_STOREYS = 4
_LETTERS = "ABCDEF"


def _lines(spans: list[int]) -> list[int]:
    out = [0]
    for span in spans:
        out.append(out[-1] + span)
    return out


def _length(start: tuple[float, float, float], end: tuple[float, float, float]) -> int:
    return int(round(math.dist(start, end)))


def _point(values: tuple[float, float, float]) -> list[int]:
    return [int(round(v)) for v in values]


def members() -> list[dict[str, object]]:
    xs = _lines(_X_SPANS)
    ys = _lines(_Y_SPANS)
    out: list[dict[str, object]] = []

    def add(
        member_id: str,
        kind: str,
        profile: str,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
    ) -> None:
        out.append({
            "id": member_id,
            "type": kind,
            "profile": profile,
            "material": MATERIAL,
            "mark": "",
            "start": _point(start),
            "end": _point(end),
            "length": _length(start, end),
        })

    for storey in range(1, _STOREYS + 1):
        z0 = (storey - 1) * _STOREY_HEIGHT
        z1 = storey * _STOREY_HEIGHT
        column_profile = "HEA300" if storey <= 2 else "HEA240"
        for xi, x in enumerate(xs):
            for yi, y in enumerate(ys):
                add(f"C-{_LETTERS[xi]}{yi + 1}-{storey}", "column", column_profile,
                    (x, y, z0), (x, y, z1))

    for floor in range(1, _STOREYS + 1):
        z = floor * _STOREY_HEIGHT
        for yi, y in enumerate(ys):
            for xi, (x0, x1) in enumerate(zip(xs, xs[1:], strict=False)):
                add(f"B-X-{_LETTERS[xi]}{yi + 1}-{floor}", "beam", "IPE360",
                    (x0, y, z), (x1, y, z))
        for xi, x in enumerate(xs):
            for yi, (y0, y1) in enumerate(zip(ys, ys[1:], strict=False)):
                add(f"B-Y-{_LETTERS[xi]}{yi + 1}-{floor}", "beam", "IPE300",
                    (x, y0, z), (x, y1, z))
        for xi, (x0, x1) in enumerate(zip(xs, xs[1:], strict=False)):
            for yi, (y0, y1) in enumerate(zip(ys, ys[1:], strict=False)):
                third = (y1 - y0) / 3
                for idx, y in enumerate((y0 + third, y0 + 2 * third), start=1):
                    add(f"S-{_LETTERS[xi]}{yi + 1}-{floor}-{idx}", "secondary", "IPE220",
                        (x0, y, z), (x1, y, z))

    for storey in range(1, _STOREYS + 1):
        z0 = (storey - 1) * _STOREY_HEIGHT
        z1 = storey * _STOREY_HEIGHT
        for side, y in (("N", ys[0]), ("S", ys[-1])):
            for xi, (x0, x1) in enumerate(zip(xs, xs[1:], strict=False)):
                add(f"BR-{side}-{_LETTERS[xi]}-{storey}-A", "brace", "CHS168.3x6.3",
                    (x0, y, z0), (x1, y, z1))
                add(f"BR-{side}-{_LETTERS[xi]}-{storey}-B", "brace", "CHS168.3x6.3",
                    (x1, y, z0), (x0, y, z1))

    # Roof canopy: 4.1 m cantilevers fit market bars badly, so the demo shows a real high-waste warning.
    roof = _STOREYS * _STOREY_HEIGHT
    for xi, x in enumerate(xs):
        add(f"K-{_LETTERS[xi]}", "canopy", "RHS150x100x5", (x, ys[-1], roof), (x, ys[-1] + 4100, roof))

    prefixes = {"column": "C", "beam": "B", "secondary": "S", "brace": "BR", "canopy": "K"}
    counters: dict[str, int] = {}
    marks: dict[tuple[str, int, str], str] = {}
    for member in out:
        key = (str(member["profile"]), int(member["length"]), str(member["material"]))
        if key not in marks:
            prefix = prefixes[str(member["type"])]
            counters[prefix] = counters.get(prefix, 0) + 1
            marks[key] = f"{prefix}{counters[prefix]}"
        member["mark"] = marks[key]

    return out


def payload() -> dict[str, object]:
    return {"name": "M13S demo frame — 4 storeys", "members": members()}


def write_model(path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parts():
    raw = [
        {
            "reference": member["mark"],
            "length": member["length"],
            "profile": member["profile"],
            "material": member["material"],
        }
        for member in members()
    ]
    return _group_parts(raw)


if __name__ == "__main__":
    print(write_model())

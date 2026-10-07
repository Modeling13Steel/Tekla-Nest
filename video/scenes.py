"""Parse docs/demo-video/script-master.md -> video/build/scenes.json (the only source of truth)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "docs/demo-video/script-master.md"
OUT = ROOT / "video/build/scenes.json"
CUTS = {"teaser": {1}, "short": {1, 2}, "full": {1, 2, 3}}  # cut -> allowed priorities


def _rows(md: str, header: str) -> list[list[str]]:
    section = md.split(header, 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if re.match(r"\|\s*\d+\s*\|", r)]
    return [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]


def _unquote(s: str) -> str:
    return s.strip().strip('"')


def parse(md: str) -> dict:
    scenes = {}
    for c in _rows(md, "## Scenes"):
        n, beat, render, interaction, transition, sfx, vo, caption, p, secs = c
        scenes[int(n)] = {
            "n": int(n), "beat": beat, "p": int(p), "seconds": float(secs),
            "render": render, "interaction": interaction, "transition": transition, "sfx": sfx,
            "vo": {"en": _unquote(vo)}, "caption": {"en": caption},
        }
    for n, vo, caption in _rows(md, "## pt-PT VO and captions"):
        scenes[int(n)]["vo"]["pt"] = _unquote(vo)
        scenes[int(n)]["caption"]["pt"] = caption
    ordered = [scenes[k] for k in sorted(scenes)]
    cuts = {name: [s["n"] for s in ordered if s["p"] in ps] for name, ps in CUTS.items()}
    return {"scenes": ordered, "cuts": cuts}


def main() -> None:
    data = parse(SCRIPT.read_text(encoding="utf-8"))
    assert len(data["scenes"]) == 14 and all("pt" in s["vo"] for s in data["scenes"])
    assert data["cuts"]["teaser"] == [3, 8, 14] and data["cuts"]["short"] == [3, 6, 7, 8, 14]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['scenes'])} scenes, cuts={data['cuts']}")


if __name__ == "__main__":
    main()

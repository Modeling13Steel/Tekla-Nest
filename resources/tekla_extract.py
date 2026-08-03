"""Standalone Tekla extraction helper – run by system Python, not PyInstaller.

This script is designed to be executed via ``subprocess`` by the frozen
application.  It connects to a running Tekla Structures instance, reads
the selected objects, and prints them as a JSON array on stdout.

Usage (called from the frozen app)::

    python tekla_extract.py <tekla_bin_path>

Exit codes:
    0 – success (JSON on stdout)
    1 – runtime error (message on stderr)
    2 – pythonnet not available

Requires:
    • pythonnet (``pip install pythonnet``)
    • A running Tekla Structures instance with selected objects
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Plate profile prefixes to filter out.
_PLATE_TOKENS = ("PL", "CHA")

# Sub-directories that may contain Open API assemblies.
_ASSEMBLY_SUBDIRS = ("", "Net48Runtime")

# Tekla .NET namespaces to load.
_NAMESPACES = ("Tekla.Structures", "Tekla.Structures.Model")


def _load_assemblies(bin_path: str) -> None:
    import clr  # type: ignore[import-not-found]

    bin_dir = Path(bin_path)
    probe_dirs = [bin_dir]
    for sub in _ASSEMBLY_SUBDIRS:
        if sub:
            candidate = bin_dir / sub
            if candidate.is_dir():
                probe_dirs.append(candidate)

    for d in probe_dirs:
        s = str(d.resolve())
        if s not in sys.path:
            sys.path.insert(0, s)

    for ns in _NAMESPACES:
        clr.AddReference(ns)


def _extract_parts(bin_path: str) -> dict:
    _load_assemblies(bin_path)

    from Tekla.Structures.Model import UI, Model  # type: ignore[import-not-found]

    model = Model()
    if not model.GetConnectionStatus():
        raise RuntimeError(
            "Cannot connect to Tekla Structures.  "
            "Ensure the application is running and a model is open."
        )

    try:
        info = model.GetProjectInfo()
        project_name = str(info.Name or "").strip()
    except Exception:
        project_name = ""

    parts: list[dict] = []
    enum = UI.ModelObjectSelector().GetSelectedObjects()
    while enum.MoveNext():
        obj = enum.Current

        found_p, profile = obj.GetReportProperty("PROFILE", "")
        if not found_p or not profile:
            continue
        if any(tok in profile.upper() for tok in _PLATE_TOKENS):
            continue

        found_r, reference = obj.GetReportProperty("PART_POS", "")
        if not found_r or not reference:
            continue

        found_l, length = obj.GetReportProperty("LENGTH", 0.0)
        if not found_l or length <= 0:
            continue

        _, material = obj.GetReportProperty("MATERIAL", "")

        parts.append({
            "reference": reference,
            "length": float(length),
            "profile": profile,
            "material": material or "",
        })

    return {"parts": parts, "project_name": project_name}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: tekla_extract.py <tekla_bin_path>", file=sys.stderr)
        return 1

    bin_path = sys.argv[1]

    try:
        import clr  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        print(
            "pythonnet is not installed in the system Python.\n"
            "Install with:  pip install pythonnet",
            file=sys.stderr,
        )
        return 2

    try:
        payload = _extract_parts(bin_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

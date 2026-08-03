"""Provider that loads selected bar parts from a running Tekla Structures instance.

When running from source (``pythonnet`` importable), the provider uses the
Tekla Open API directly.  Inside a frozen PyInstaller bundle – where
pythonnet cannot initialise – it spawns a small helper script
(``resources/tekla_extract.py``) via the **system** Python, which *does*
have pythonnet installed, and reads the results back as JSON.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..models import PartEntry
from .base_provider import PartProvider

log = logging.getLogger(__name__)

# Plate profile prefixes to filter out (same as C# logic).
_PLATE_TOKENS = ("PL", "CHA")


def _no_console_kwargs() -> dict:
    """Return subprocess kwargs that suppress the transient console
    window on Windows. No-op on POSIX."""
    if sys.platform == "win32":
        # CREATE_NO_WINDOW is only defined on Windows builds of subprocess.
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def _group_parts(raw_parts: list[dict[str, object]]) -> list[PartEntry]:
    grouped: dict[str, dict[str, object]] = {}
    for part in raw_parts:
        ref = str(part["reference"])
        if ref not in grouped:
            grouped[ref] = {**part, "quantity": 0}
        grouped[ref]["quantity"] = int(grouped[ref]["quantity"]) + 1  # type: ignore[arg-type]

    return [
        PartEntry(
            quantity=int(g["quantity"]),  # type: ignore[arg-type]
            length=float(g["length"]),  # type: ignore[arg-type]
            reference=str(g["reference"]),
            profile=str(g["profile"]),
            material=str(g["material"]),
        )
        for g in grouped.values()
    ]


def _is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _find_bundled_python() -> str | None:
    """Locate the bundled embeddable Python shipped with the installer.

    The installer places a portable Python (with pythonnet pre-installed)
    at ``<install_dir>/python/python.exe``.  For a PyInstaller onedir
    bundle the install dir is the parent of ``sys._MEIPASS``.
    """
    if not _is_frozen():
        return None

    # onedir: _MEIPASS is the bundle folder itself, which lives inside
    # the install dir  (e.g. C:\Program Files\Tekla Nest Optimizer\tekla-nest)
    base = Path(sys.executable).parent  # the dir containing tekla-nest.exe
    candidate = base / "python" / "python.exe"
    if candidate.is_file():
        return str(candidate)
    return None


def _find_system_python() -> str | None:
    """Locate a system Python that has pythonnet installed.

    Checks common locations; the frozen app ships its own Python but
    that one cannot run pythonnet, so we need to find the real one.
    """
    candidates: list[str] = []

    # 1. py launcher (preferred on Windows – picks the right version)
    py = shutil.which("py")
    if py:
        candidates.append(py)

    # 2. python / python3 on PATH
    for name in ("python", "python3"):
        p = shutil.which(name)
        if p:
            candidates.append(p)

    # 3. Common Windows install locations
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        prog = os.environ.get("ProgramFiles", r"C:\Program Files")
        for base in (local, prog):
            if not base:
                continue
            for child in Path(base).glob("Python*/python.exe"):
                candidates.append(str(child))

    for candidate in candidates:
        # Skip *our own* bundled Python
        if _is_frozen():
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass and candidate.startswith(meipass):
                continue

        # Quick check: can this Python import clr?
        try:
            proc = subprocess.run(
                [candidate, "-c", "import clr"],
                capture_output=True,
                timeout=10,
                **_no_console_kwargs(),
            )
            if proc.returncode == 0:
                log.info("System Python with pythonnet: %s", candidate)
                return candidate
        except Exception:
            continue

    return None


def _find_helper_script() -> str:
    """Locate ``tekla_extract.py`` shipped next to the binary."""
    if _is_frozen():
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[2]  # project root

    for candidate in (
        base / "resources" / "tekla_extract.py",
        base / "tekla_extract.py",
    ):
        if candidate.is_file():
            return str(candidate)

    raise FileNotFoundError(
        "tekla_extract.py not found in the application bundle.\n"
        "Expected at: resources/tekla_extract.py"
    )


class TeklaPartProvider(PartProvider):
    """Loads selected bar parts from Tekla, filtering out plates.

    Groups by PART_POS reference and counts quantity, exactly like
    the original C# FILTRAR() method.
    """

    def __init__(self) -> None:
        self.project_name: str = ""

    def get_parts(self) -> list[PartEntry]:
        from ..services.tekla_api import find_tekla_bin

        bin_path = find_tekla_bin()
        if not bin_path:
            raise RuntimeError(
                "Could not find Tekla Structures installation.\n\n"
                "Set one of these environment variables:\n"
                "  TEKLA_BIN_PATH, TEKLA_PATH, TeklaPath"
            )

        if _is_frozen():
            raw, project_name = self._load_via_subprocess(bin_path)
        else:
            raw, project_name = self._load_in_process(bin_path)

        self.project_name = project_name
        return _group_parts(raw)

    # ── Strategy 1: subprocess (frozen binary) ───────────────

    def _load_via_subprocess(self, bin_path: str) -> tuple[list[dict], str]:
        python = _find_bundled_python() or _find_system_python()
        if python is None:
            raise RuntimeError(
                "Could not find a Python installation with pythonnet.\n\n"
                "Re-install the application using the installer, or\n"
                "install Python and pythonnet manually:\n"
                "  1. Install Python from https://python.org\n"
                "  2. Run:  pip install pythonnet"
            )

        helper = _find_helper_script()
        log.info("Running Tekla helper: %s %s %s", python, helper, bin_path)

        proc = subprocess.run(
            [python, helper, bin_path],
            capture_output=True,
            text=True,
            timeout=60,
            **_no_console_kwargs(),
        )

        if proc.returncode == 2:
            raise RuntimeError(
                "The system Python does not have pythonnet installed.\n"
                "Run:  pip install pythonnet"
            )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Tekla extraction failed")

        data = json.loads(proc.stdout)
        if isinstance(data, dict):
            return data.get("parts", []), str(data.get("project_name", "") or "")
        return data, ""

    # ── Strategy 2: in-process (running from source) ─────────

    @staticmethod
    def _load_in_process(bin_path: str) -> tuple[list[dict], str]:
        from ..services.tekla_api import (
            connect_model,
            get_project_name,
            get_report_property,
            get_selected_objects,
            load_tekla_assemblies,
        )

        load_tekla_assemblies(bin_path)
        model = connect_model()
        project_name = get_project_name(model)

        raw: list[dict[str, object]] = []
        for obj in get_selected_objects(model):
            profile = get_report_property(obj, "PROFILE", "") or ""
            if any(tok in profile.upper() for tok in _PLATE_TOKENS):
                continue

            reference = get_report_property(obj, "PART_POS", "") or ""
            length = float(get_report_property(obj, "LENGTH", 0.0) or 0)
            material = get_report_property(obj, "MATERIAL", "") or ""

            if not profile or not reference or length <= 0:
                continue

            raw.append({
                "reference": reference,
                "length": length,
                "profile": profile,
                "material": material,
            })

        return raw, project_name

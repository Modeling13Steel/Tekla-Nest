"""Lightweight bridge to the Tekla Structures Open API via pythonnet.

Only place in the codebase that touches CLR / .NET.  Provides:

    1. Tekla bin folder discovery  (env → registry → process → filesystem)
    2. Assembly loading via ``clr.AddReference``
    3. Model connection, object iteration, report property access

Requires ``pythonnet`` (the ``clr`` module).  Works with Tekla 2021 – 2026+.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────

_REGISTRY_ROOTS = (
    r"SOFTWARE\Tekla\Structures",          # Tekla ≤ 2022
    r"SOFTWARE\Trimble\Tekla Structures",  # Tekla 2023+
)

_NAMESPACES = ("Tekla.Structures", "Tekla.Structures.Model")

# Subdirectories that may contain Open API assemblies.
# Tekla 2026+ moved Tekla.Structures.dll into Net48Runtime/.
# Older versions keep everything in the bin root.
_ASSEMBLY_SUBDIRS = ("", "Net48Runtime")

# Default install locations (glob-friendly).  The wildcard picks up
# versioned folders like "2024.0", "2026.0", etc.
_INSTALL_GLOBS = (
    r"C:\TeklaStructures\*",
    r"C:\Program Files\Tekla Structures\*",
    r"C:\Program Files\Trimble\Tekla Structures\*",
    r"C:\Program Files (x86)\Tekla Structures\*",
    r"C:\Program Files (x86)\Trimble\Tekla Structures\*",
)


# ── Path discovery ───────────────────────────────────────────


def resolve_tekla_bin(path: str | os.PathLike[str] | None) -> str | None:
    """Normalise a path (install root, bin dir, or exe) to a bin folder.

    Returns the bin folder string if it exists, else ``None``.
    """
    if not path:
        return None
    p = Path(str(path).strip().strip('"'))
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        return None
    bin_sub = p / "bin"
    return str(bin_sub) if bin_sub.is_dir() else str(p)


def _find_via_env() -> str | None:
    for var in ("TEKLA_BIN_PATH", "TEKLA_PATH", "TeklaPath"):
        result = resolve_tekla_bin(os.environ.get(var))
        if result:
            return result
    return None


def _find_via_registry() -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    flags = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for root in _REGISTRY_ROOTS:
            result = _probe_registry_key(winreg, hive, root, flags)
            if result:
                return result
    return None


def _probe_registry_key(winreg, hive, base_key: str, flags: int) -> str | None:
    try:
        with winreg.OpenKey(hive, base_key, 0, flags) as key:
            # Check values directly on the base key.
            result = _read_path_values(winreg, key)
            if result:
                return result
            # Enumerate versioned sub-keys (newest first).
            versions = []
            i = 0
            while True:
                try:
                    versions.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
    except OSError:
        return None

    for ver in sorted(versions, reverse=True):
        try:
            with winreg.OpenKey(hive, rf"{base_key}\{ver}", 0, flags) as vk:
                result = _read_path_values(winreg, vk)
                if result:
                    return result
        except OSError:
            continue
    return None


def _read_path_values(winreg, key) -> str | None:
    for name in ("InstallPath", "Path"):
        try:
            val, _ = winreg.QueryValueEx(key, name)
        except OSError:
            continue
        result = resolve_tekla_bin(val)
        if result:
            return result
    return None


def _find_via_process() -> str | None:
    """Detect Tekla from a running TeklaStructures.exe process."""
    # Windows-only routine, but guard CREATE_NO_WINDOW for safety.
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for cmd in _process_commands():
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, check=False,
                **kwargs,
            )
        except Exception:
            continue
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("ExecutablePath="):
                line = line.split("=", 1)[1].strip()
            result = resolve_tekla_bin(line)
            if result:
                return result
    return None


def _process_commands() -> list[list[str]]:
    cmds: list[list[str]] = []
    for shell in ("powershell", "pwsh"):
        if shutil.which(shell):
            cmds.append([
                shell, "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Process "
                "-Filter \"Name = 'TeklaStructures.exe'\" "
                "| Select-Object -ExpandProperty ExecutablePath)",
            ])
    if shutil.which("wmic"):
        cmds.append([
            "wmic", "process", "where", "name='TeklaStructures.exe'",
            "get", "ExecutablePath", "/format:list",
        ])
    return cmds


def _find_via_filesystem() -> str | None:
    """Scan common install directories for any Tekla version."""
    import glob as _glob

    candidates = []
    for pattern in _INSTALL_GLOBS:
        candidates.extend(_glob.glob(pattern))
    valid = [r for c in candidates if (r := resolve_tekla_bin(c))]
    return max(valid) if valid else None


def find_tekla_bin() -> str | None:
    """Auto-detect the Tekla Structures bin folder.

    Probes in order: environment variables → Windows registry →
    running process → filesystem scan.  Returns ``None`` on non-Windows.
    """
    if sys.platform != "win32":
        return None
    for finder in (_find_via_env, _find_via_registry, _find_via_process, _find_via_filesystem):
        result = finder()
        if result:
            log.info("Tekla bin found via %s: %s", finder.__name__, result)
            return result
    return None


# ── Assembly loading ─────────────────────────────────────────


def load_tekla_assemblies(bin_path: str) -> None:
    """Register Tekla Open API assemblies with pythonnet.

    Adds the bin folder (and known subdirectories like ``Net48Runtime/``)
    to ``sys.path`` so that ``clr.AddReference`` can find assemblies by
    name.  This lets .NET resolve transitive dependencies automatically.

    Works across Tekla versions:

    * **2021 – 2025**: all Open API DLLs live in the bin root.
    * **2026+**: ``Tekla.Structures.dll`` moved to ``bin/Net48Runtime/``.
    """
    try:
        import clr  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "pythonnet is not installed.\n"
            "  Fix: pip install \"pythonnet>=3.0.3\""
        ) from exc
    except RuntimeError as exc:
        raise RuntimeError(
            "pythonnet failed to initialise (Python.Runtime.dll could not be loaded).\n"
            "This usually means the installed pythonnet version is incompatible with "
            "your Python version.\n"
            f"  Detail: {exc}\n"
            "  Fix: pip install \"pythonnet>=3.0.3\"\n"
            "  If the error persists, verify your Python version is 3.9–3.12."
        ) from exc

    bin_dir = Path(bin_path)
    if not bin_dir.is_dir():
        raise RuntimeError(f"Tekla bin folder not found: {bin_dir}")

    # Build probe list: bin root + any existing subdirectories.
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
        try:
            clr.AddReference(ns)
        except Exception as exc:
            searched = [str(d.resolve()) for d in probe_dirs]
            raise RuntimeError(
                f"Failed to load {ns}.\n"
                f"Searched: {searched}\n"
                "Verify the folders contain the Tekla Open API DLLs."
            ) from exc

# ── Model interaction ────────────────────────────────────────


def connect_model():
    """Return a connected ``Tekla.Structures.Model.Model`` instance."""
    from Tekla.Structures.Model import Model  # type: ignore[import-not-found]

    model = Model()
    if not model.GetConnectionStatus():
        raise RuntimeError(
            "Cannot connect to Tekla Structures.  "
            "Ensure the application is running and a model is open."
        )
    return model


def get_selected_objects(model):
    """Yield model objects from the current selection."""
    from Tekla.Structures.Model import UI  # type: ignore[import-not-found]

    enum = UI.ModelObjectSelector().GetSelectedObjects()
    while enum.MoveNext():
        yield enum.Current


def get_project_name(model) -> str:
    """Return the active model's project name from ProjectInfo, or '' on any error."""
    try:
        info = model.GetProjectInfo()
        return str(info.Name or "").strip()
    except Exception:
        return ""


def get_report_property(
    obj,
    name: str,
    default: str | int | float,
) -> str | int | float | None:
    """Read a report property from a model object.

    *default* acts as the .NET type hint: pass ``""`` for strings,
    ``0.0`` for doubles, ``0`` for ints.  Returns ``None`` if the
    property is not found.
    """
    found, value = obj.GetReportProperty(name, default)
    return value if found else None

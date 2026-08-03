"""Machine fingerprint generation and 2-of-3 comparison (Windows only)."""

from __future__ import annotations

import hashlib
import platform


def _sha256_component(value: str) -> str:
    """SHA-256 a single component string → hex digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_cpu_id() -> str:
    """Read Win32_Processor.ProcessorId via WMI."""
    import wmi  # type: ignore[import-untyped]

    conn = wmi.WMI()
    procs = conn.Win32_Processor()
    if not procs:
        return ""
    return procs[0].ProcessorId or ""


def _get_motherboard_serial() -> str:
    """Read Win32_BaseBoard.SerialNumber via WMI."""
    import wmi  # type: ignore[import-untyped]

    conn = wmi.WMI()
    boards = conn.Win32_BaseBoard()
    if not boards:
        return ""
    return boards[0].SerialNumber or ""


def _get_machine_guid() -> str:
    """Read HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid from the registry."""
    import winreg  # type: ignore[import-error]  # Windows-only stdlib

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except OSError:
        return ""


# ── Public API ────────────────────────────────────────────────────────────


def get_fingerprint_components() -> tuple[str, str, str]:
    """Return *(cpu_hash, mb_hash, guid_hash)* for the current machine."""
    if platform.system() != "Windows":
        raise RuntimeError("Machine fingerprinting requires Windows (WMI is unavailable)")
    cpu_hash = _sha256_component(_get_cpu_id())
    mb_hash = _sha256_component(_get_motherboard_serial())
    guid_hash = _sha256_component(_get_machine_guid())
    return cpu_hash, mb_hash, guid_hash


def get_machine_fingerprint() -> str:
    """Compute the full fingerprint string (``cpu:mb:guid`` hex hashes)."""
    cpu, mb, guid = get_fingerprint_components()
    return f"{cpu}:{mb}:{guid}"


def combined_hash(cpu: str, mb: str, guid: str) -> str:
    """SHA-256 the concatenation of three component hashes → single hex hash."""
    return hashlib.sha256((cpu + mb + guid).encode("ascii")).hexdigest()


def match_fingerprint(stored: str, current_components: tuple[str, str, str]) -> bool:
    """Return ``True`` if at least 2 of 3 component hashes match."""
    parts = stored.split(":")
    if len(parts) != 3:
        return False
    matches = sum(1 for s, c in zip(parts, current_components, strict=False) if s == c)
    return matches >= 2

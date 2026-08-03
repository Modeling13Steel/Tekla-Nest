"""Machine fingerprinting — deterministic hardware ID.

Combines multiple signals (MAC, hostname, platform, CPU count) into
a single SHA-256 hash so that no single value can be trivially spoofed.
"""
from __future__ import annotations

import hashlib
import platform
import uuid


def get_machine_id() -> str:
    """Return a deterministic SHA-256 hex digest identifying this machine."""
    parts = [
        # MAC address of the default NIC (most stable identifier)
        hex(uuid.getnode()),
        # Hostname
        platform.node(),
        # OS family + version
        platform.system(),
        platform.release(),
        # Architecture
        platform.machine(),
        # CPU count as string
        str(_cpu_count()),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cpu_count() -> int:
    import os
    return os.cpu_count() or 1

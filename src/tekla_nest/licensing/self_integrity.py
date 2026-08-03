"""Binary self-integrity verification via XOR-obfuscated hash comparison.

Post-build workflow
-------------------
1. Build the frozen executable with PyInstaller.
2. Run::

       python -m tekla_nest.licensing.self_integrity <path/to/exe>

3. Copy the printed ``_XOR_KEY`` and ``_EXPECTED_HASH_XOR`` byte literals
   into this module, replacing the sentinels below.
4. Rebuild so the patched module is bundled into the final binary.

The check is **skipped** when running from source (unfrozen).
"""

from __future__ import annotations

import hashlib
import sys

from .models import Err, Ok

# ── XOR-obfuscated expected binary hash (32 bytes each) ──────────────────
# All-0xFF = unconfigured sentinel — update via the CLI (see docstring).
_EXPECTED_HASH_XOR: bytes = (
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
)

_XOR_KEY: bytes = (
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff"
)

_SENTINEL = b"\xff" * 32


def _deobfuscate(data: bytes, key: bytes) -> bytes:
    """XOR-deobfuscate *data* with a repeating *key*."""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


def _hash_executable() -> bytes:
    """SHA-256 the current frozen executable."""
    with open(sys.executable, "rb") as fh:
        return hashlib.sha256(fh.read()).digest()


def check_binary_integrity() -> Ok[None] | Err:
    """Verify the running binary against the embedded obfuscated hash."""
    if not getattr(sys, "frozen", False):
        # Development mode — nothing to verify.
        return Ok(None)

    if _EXPECTED_HASH_XOR == _SENTINEL:
        return Err(
            "Binary integrity check is not configured.  "
            "Run: python -m tekla_nest.licensing.self_integrity <exe_path>"
        )

    expected = _deobfuscate(_EXPECTED_HASH_XOR, _XOR_KEY)
    actual = _hash_executable()
    if actual != expected:
        return Err("Binary integrity check failed: executable has been modified")
    return Ok(None)


def compute_obfuscated_hash(exe_path: str, xor_key: bytes) -> bytes:
    """Compute the XOR-obfuscated SHA-256 hash of *exe_path*."""
    with open(exe_path, "rb") as fh:
        raw = hashlib.sha256(fh.read()).digest()
    return bytes(h ^ xor_key[i % len(xor_key)] for i, h in enumerate(raw))


# ── CLI entry-point for post-build hash generation ────────────────────────

if __name__ == "__main__":
    import argparse
    import os
    import secrets

    parser = argparse.ArgumentParser(
        description="Generate XOR-obfuscated SHA-256 hash for self-integrity"
    )
    parser.add_argument("exe_path", help="Path to the built executable")
    args = parser.parse_args()

    if not os.path.isfile(args.exe_path):
        print(f"Error: file not found: {args.exe_path}", file=sys.stderr)
        sys.exit(1)

    key = secrets.token_bytes(32)
    obfuscated = compute_obfuscated_hash(args.exe_path, key)

    def _fmt(b: bytes, name: str) -> str:
        lines = [f"{name}: bytes = ("]
        for i in range(0, len(b), 8):
            chunk = b[i : i + 8]
            hex_lit = "".join(f"\\x{byte:02x}" for byte in chunk)
            lines.append(f'    b"{hex_lit}"')
        lines.append(")")
        return "\n".join(lines)

    print("# Paste into self_integrity.py, replacing the sentinels:\n")
    print(_fmt(key, "_XOR_KEY"))
    print()
    print(_fmt(obfuscated, "_EXPECTED_HASH_XOR"))

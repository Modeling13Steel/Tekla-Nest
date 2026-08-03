"""Async activation client with TLS certificate pinning."""

from __future__ import annotations

import os
import pathlib
import sys

import httpx

from .license_crypto import get_public_key_bytes, verify_signature
from .models import Err, LicenseFile, Ok


def _get_data_dir(app_name: str) -> pathlib.Path:
    """Return ``%APPDATA%/<app_name>``, creating it if needed."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        appdata = str(pathlib.Path.home() / "AppData" / "Roaming")
    path = pathlib.Path(appdata) / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_cert_path() -> str:
    """Resolve ``server_cert.pem`` relative to the package or *_MEIPASS*."""
    if getattr(sys, "frozen", False):
        base = pathlib.Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = pathlib.Path(__file__).resolve().parent
    return str(base / "server_cert.pem")


def license_path(app_name: str) -> pathlib.Path:
    """Return the on-disk path to the saved license file."""
    return _get_data_dir(app_name) / "license.lic"


async def activate(
    server_url: str,
    license_key: str,
    machine_fingerprint: str,
    app_name: str,
    cert_path: str | None = None,
) -> Ok[LicenseFile] | Err:
    """Activate a license via HTTPS POST; save to disk on success."""
    # ── Resolve TLS verify parameter ──
    if cert_path is not None:
        if not os.path.isfile(cert_path):
            return Err(f"TLS certificate file not found: {cert_path}")
        verify: str | bool = cert_path
    else:
        resolved = _resolve_cert_path()
        verify = resolved if os.path.isfile(resolved) else True

    # ── POST /activate ──
    try:
        async with httpx.AsyncClient(verify=verify, timeout=30.0) as client:
            response = await client.post(
                f"{server_url.rstrip('/')}/activate",
                json={
                    "license_key": license_key,
                    "machine_fingerprint": machine_fingerprint,
                },
            )
    except Exception as exc:
        return Err(f"Activation request failed: {exc}")

    if response.status_code != 200:
        return Err(
            f"Activation server returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    # ── Parse & verify before saving ──
    try:
        lic = LicenseFile.from_json(response.text)
    except (KeyError, ValueError) as exc:
        return Err(f"Invalid license payload from server: {exc}")

    if not verify_signature(
        lic.signable_bytes(), lic.signature, get_public_key_bytes()
    ):
        return Err("Server returned a license with an invalid signature")

    # ── Persist to disk ──
    dest = license_path(app_name)
    try:
        dest.write_text(lic.to_json(), encoding="utf-8")
    except OSError as exc:
        return Err(f"Failed to save license file: {exc}")

    return Ok(lic)

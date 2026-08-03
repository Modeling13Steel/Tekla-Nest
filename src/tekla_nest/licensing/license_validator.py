"""Load, parse, and fully validate a license file from disk."""

from __future__ import annotations

from datetime import UTC, datetime

from .activation_client import license_path
from .license_crypto import get_public_key_bytes, verify_signature
from .machine_id import get_fingerprint_components, match_fingerprint
from .models import Err, LicenseFile, Ok


def load_license(app_name: str) -> Ok[LicenseFile] | Err:
    """Load and deserialize the license file from ``%APPDATA%``."""
    path = license_path(app_name)
    if not path.is_file():
        return Err(f"License file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Err(f"Cannot read license file: {exc}")
    try:
        lic = LicenseFile.from_json(text)
    except (KeyError, ValueError) as exc:
        return Err(f"Malformed license file: {exc}")
    return Ok(lic)


def validate_signature(lic: LicenseFile) -> Ok[None] | Err:
    """Verify the Ed25519 signature on *lic*."""
    if not verify_signature(
        lic.signable_bytes(), lic.signature, get_public_key_bytes()
    ):
        return Err("License signature is invalid")
    return Ok(None)


def validate_expiry(lic: LicenseFile) -> Ok[None] | Err:
    """Check that the license has not expired (skips if *expires_at* is ``None``)."""
    if lic.expires_at is None:
        return Ok(None)
    try:
        expires = datetime.fromisoformat(lic.expires_at)
    except ValueError:
        return Err(f"Invalid expires_at format: {lic.expires_at}")
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        return Err(f"License expired on {lic.expires_at}")
    return Ok(None)


def validate_fingerprint(lic: LicenseFile) -> Ok[None] | Err:
    """Check the license fingerprint matches this machine (2-of-3 tolerance)."""
    try:
        components = get_fingerprint_components()
    except RuntimeError as exc:
        return Err(str(exc))
    if not match_fingerprint(lic.machine_fingerprint, components):
        return Err("License is not valid for this machine")
    return Ok(None)


def load_and_validate(app_name: str) -> Ok[LicenseFile] | Err:
    """Load, parse, and fully validate the on-disk license."""
    result = load_license(app_name)
    if isinstance(result, Err):
        return result
    lic = result.value

    sig = validate_signature(lic)
    if isinstance(sig, Err):
        return sig

    exp = validate_expiry(lic)
    if isinstance(exp, Err):
        return exp

    fp = validate_fingerprint(lic)
    if isinstance(fp, Err):
        return fp

    return Ok(lic)

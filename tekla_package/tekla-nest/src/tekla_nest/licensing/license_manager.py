"""License manager — activation, validation, and local token storage.

The manager handles:
  - First-time activation (requires internet)
  - Offline JWT verification (public key embedded in the app)
  - Periodic re-validation every N days
  - Machine-bound encrypted token storage (can't copy between machines)
"""

from __future__ import annotations

import binascii
import contextlib
import hashlib
import json
import logging
import os
import time
from base64 import b64decode, b64encode
from pathlib import Path
from typing import Any

import jwt
import requests
from tekla_common.config.app_config import get_config

from . import get_machine_id

log = logging.getLogger(__name__)

# Re-validate every 30 days (configurable in config.yaml)
_DEFAULT_REVALIDATION_DAYS = 30

_PUBLIC_KEY_FILE = Path(__file__).parent / "public_key.pem"

_TOKEN_DIR = Path.home() / ".teklanest"
_TOKEN_FILE = _TOKEN_DIR / "license.dat"


class LicenseError(Exception):
    """Raised when the license is invalid, expired, or revoked."""


class LicenseNetworkError(LicenseError):
    """Raised when the license server cannot be reached."""


class LicenseManager:
    """Manages license activation, storage, and validation."""

    def __init__(self) -> None:
        cfg = get_config()
        self._server_url: str = cfg.license_server_url.strip().rstrip("/")
        self._revalidation_days: int = cfg.revalidation_days
        self._machine_id: str = get_machine_id()
        self._public_key: str = self._load_public_key()
        self._license_key: str | None = None
        self._token: str | None = None

    # ── Public API ────────────────────────────────────────────

    def is_activated(self) -> bool:
        """Check if a valid local token exists."""
        try:
            self._load_and_verify()
            return True
        except LicenseError:
            return False

    def activate(self, license_key: str) -> dict:
        """Activate a license key (requires internet).

        Returns the server response dict on success.
        Raises LicenseError on failure.
        """
        data = self._post_json(
            "activate",
            {
                "license_key": license_key,
                "machine_id": self._machine_id,
            },
        )

        self._license_key = license_key
        token = _require_string(data, "token", "Activation response did not include a token.")
        self._token = token
        self._save_token(license_key, token)

        log.info("License activated for %s", data.get("customer", ""))
        return data

    def validate(self) -> None:
        """Validate the current license.

        1. Verify local JWT signature + expiry (offline).
        2. If re-validation interval exceeded, phone home.

        Raises LicenseError if invalid.
        """
        payload = self._load_and_verify()
        self._license_key = payload.get("sub", "")

        # Check if we need to re-validate online
        last_check = self._last_validation_time()
        days_since = (time.time() - last_check) / 86400

        if days_since >= self._revalidation_days:
            self._revalidate_online()

    def deactivate(self) -> None:
        """Remove local license token."""
        with contextlib.suppress(FileNotFoundError):
            _TOKEN_FILE.unlink()
        self._license_key = None
        self._token = None

    @property
    def license_key(self) -> str | None:
        return self._license_key

    @property
    def machine_id(self) -> str:
        return self._machine_id

    # ── HTTP and key material ──────────────────────────────────

    def _load_public_key(self) -> str:
        try:
            key = _PUBLIC_KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise LicenseError(
                "License public key is missing.\n"
                "Run license-server/scripts/generate_keys.py before building a "
                "licensed release, then rebuild the app."
            ) from exc
        if not key:
            raise LicenseError(
                "License public key is empty.\n"
                "Regenerate the license keys before building a licensed release."
            )
        return key

    def _endpoint(self, path: str) -> str:
        if not self._server_url:
            raise LicenseError(
                "License server URL is not configured.\nSet licensing.server_url in config.yaml."
            )
        return f"{self._server_url}/{path}"

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        raise_on_error: bool = True,
    ) -> dict[str, Any]:
        try:
            resp = requests.post(
                self._endpoint(path),
                json=payload,
                timeout=15,
            )
        except requests.ConnectionError as exc:
            raise LicenseNetworkError(
                "Cannot reach the license server.\n"
                "Internet access is required for first-time activation."
            ) from exc
        except requests.Timeout as exc:
            raise LicenseNetworkError("License server timed out. Try again later.") from exc
        except requests.RequestException as exc:
            raise LicenseNetworkError("License server request failed. Try again later.") from exc

        data = _response_json(resp)
        if not resp.ok and raise_on_error:
            raise LicenseError(_response_error(data, "License server request failed"))
        return data

    # ── Token storage (machine-bound encryption) ──────────────

    def _derive_key(self) -> bytes:
        """Derive a 32-byte key from the machine ID for AES-like XOR obfuscation."""
        return hashlib.sha256(self._machine_id.encode()).digest()

    def _xor_bytes(self, data: bytes) -> bytes:
        """Simple XOR with the derived key (repeating). Not AES, but
        sufficient to prevent naive file copying between machines."""
        key = self._derive_key()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _save_token(self, license_key: str, token: str) -> None:
        """Save encrypted token + metadata to disk."""
        try:
            _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LicenseError("Could not create local license storage.") from exc
        payload = json.dumps(
            {
                "license_key": license_key,
                "token": token,
                "machine_id": self._machine_id,
                "saved_at": time.time(),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        encrypted = self._xor_bytes(payload)
        tmp_file = _TOKEN_FILE.with_suffix(".tmp")
        try:
            tmp_file.write_bytes(b64encode(encrypted))
            os.chmod(tmp_file, 0o600)
            tmp_file.replace(_TOKEN_FILE)
        except OSError as exc:
            raise LicenseError("Could not save the local license file.") from exc

    def _load_token(self) -> dict:
        """Load and decrypt the local token file. Returns the parsed dict."""
        if not _TOKEN_FILE.exists():
            raise LicenseError("No license found.\nPlease activate with your license key.")
        try:
            encrypted = b64decode(_TOKEN_FILE.read_bytes(), validate=True)
            decrypted = self._xor_bytes(encrypted)
            data = json.loads(decrypted.decode("utf-8"))
        except (
            OSError,
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise LicenseError(
                "License file is corrupted or was copied from another machine.\nPlease re-activate."
            ) from exc
        if not isinstance(data, dict):
            raise LicenseError(
                "License file is corrupted or was copied from another machine.\nPlease re-activate."
            )

        if data.get("machine_id") != self._machine_id:
            raise LicenseError(
                "License was activated on a different machine.\nPlease re-activate on this machine."
            )
        if not isinstance(data.get("license_key"), str) or not isinstance(data.get("token"), str):
            raise LicenseError(
                "License file is corrupted or was copied from another machine.\nPlease re-activate."
            )
        return data

    def _load_and_verify(self) -> dict:
        """Load token from disk and verify JWT signature + expiry."""
        data = self._load_token()
        token = data.get("token", "")
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                options={"require": ["sub", "mid", "exp"]},
            )
        except jwt.ExpiredSignatureError:
            raise LicenseError("License has expired.\nContact your administrator to renew.")
        except jwt.InvalidTokenError as exc:
            raise LicenseError(f"Invalid license token: {exc}")

        if payload.get("mid") != self._machine_id:
            raise LicenseError(
                "License token was issued for a different machine.\nPlease re-activate."
            )
        self._license_key = data.get("license_key")
        self._token = token
        return payload

    def _last_validation_time(self) -> float:
        """Seconds since epoch of last server validation."""
        try:
            data = self._load_token()
            return float(data.get("saved_at", 0))
        except LicenseError:
            return 0.0

    def _revalidate_online(self) -> None:
        """Phone home to confirm license is still active."""
        try:
            data = self._post_json(
                "validate",
                {
                    "license_key": self._license_key,
                    "machine_id": self._machine_id,
                },
                raise_on_error=False,
            )
        except LicenseNetworkError:
            log.warning("Could not reach license server for re-validation")
            return  # graceful offline — use cached token

        if data.get("valid") is not True:
            if data.get("valid") is not False:
                raise LicenseError(_response_error(data, "License validation failed"))
            reason = data.get("reason", "unknown")
            self.deactivate()
            raise LicenseError(
                f"License validation failed: {reason}.\nPlease contact your administrator."
            )

        # Refresh local token with new one from server
        if data.get("token") and self._license_key:
            self._save_token(self._license_key, data["token"])
            log.info("License re-validated successfully")


def _response_json(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError as exc:
        raise LicenseError("License server returned an invalid response.") from exc
    if not isinstance(data, dict):
        raise LicenseError("License server returned an invalid response.")
    return data


def _response_error(data: dict[str, Any], fallback: str) -> str:
    message = data.get("error") or data.get("reason") or fallback
    return str(message)


def _require_string(data: dict[str, Any], key: str, error: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise LicenseError(error)
    return value

"""Ed25519 signature operations and SHA-256 helpers (PyCA *cryptography*)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

# ── Embedded Ed25519 public key (32 bytes, raw) ──────────────────────────
# Replace with your production key:  python scripts/keygen_tool.py --gen-keypair
# Default below is the RFC 8032 Test-Vector-1 public key (development only).
_EMBEDDED_PUBLIC_KEY: bytes = (
    b"\xd7\x5a\x98\x01\x82\xb1\x0a\xb7"
    b"\xd5\x4b\xfe\xd3\xc9\x64\x07\x3a"
    b"\x0e\xe1\x72\xf3\xda\xa3\xf4\xa1"
    b"\x84\x46\xb0\xb8\xd1\x83\xf8\xe3"
)


def get_public_key_bytes() -> bytes:
    """Return the embedded Ed25519 public key bytes."""
    return _EMBEDDED_PUBLIC_KEY


# ── SHA-256 helpers ───────────────────────────────────────────────────────


def sha256_hex(data: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_raw(data: bytes) -> bytes:
    """Return the raw SHA-256 digest bytes of *data*."""
    return hashlib.sha256(data).digest()


# ── Ed25519 sign / verify ────────────────────────────────────────────────


def sign(payload: bytes, private_key_seed: bytes) -> str:
    """Sign *payload* with a 32-byte Ed25519 seed; return base64url signature."""
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_seed)
    raw_sig = private_key.sign(payload)
    return base64.urlsafe_b64encode(raw_sig).decode("ascii")


def verify_signature(payload: bytes, signature_b64: str, public_key_bytes: bytes) -> bool:
    """Verify an Ed25519 *signature_b64* over *payload*.  Returns ``False`` on failure."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        raw_sig = base64.urlsafe_b64decode(signature_b64)
        pub.verify(raw_sig, payload)
        return True
    except (InvalidSignature, ValueError):
        return False


# ── Key-pair generation ───────────────────────────────────────────────────


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 keypair → *(private_seed_32, public_key_32)*."""
    private_key = Ed25519PrivateKey.generate()
    priv = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return priv, pub

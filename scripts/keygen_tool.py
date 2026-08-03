#!/usr/bin/env python3
"""Standalone CLI: generate Ed25519 keypairs and sign license files.

This script is meant for the **license server** only — never ship it with the
application.

Examples::

    # Generate a new keypair
    python scripts/keygen_tool.py --gen-keypair

    # Sign a license
    python scripts/keygen_tool.py \\
        --private-key "<base64-seed>" \\
        --license-key "ACME-0001" \\
        --email "user@example.com" \\
        --fingerprint "<cpu_hash>:<mb_hash>:<guid_hash>" \\
        --expires "2026-12-31T23:59:59+00:00" \\
        --features pro export \\
        -o license.lic
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone

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


# ── Crypto helpers (self-contained, no project imports) ───────────────────

def _generate_keypair() -> tuple[bytes, bytes]:
    """Return *(private_seed_32, public_key_32)*."""
    priv = Ed25519PrivateKey.generate()
    seed = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return seed, pub


def _sign(payload: bytes, seed: bytes) -> str:
    """Ed25519-sign *payload* with a 32-byte *seed*; return base64url."""
    key = Ed25519PrivateKey.from_private_bytes(seed)
    return base64.urlsafe_b64encode(key.sign(payload)).decode("ascii")


def _verify(payload: bytes, sig_b64: str, pub_bytes: bytes) -> bool:
    """Verify an Ed25519 signature."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
        pub.verify(base64.urlsafe_b64decode(sig_b64), payload)
        return True
    except Exception:
        return False


# ── License builder ───────────────────────────────────────────────────────

def _build_license(
    license_key: str,
    customer_email: str,
    machine_fingerprint: str,
    expires_at: str | None,
    features: list[str],
    private_seed: bytes,
) -> dict[str, object]:
    """Construct a signed license dict."""
    issued_at = datetime.now(timezone.utc).isoformat()

    # Canonical signable JSON — must match LicenseFile.signable_bytes()
    signable = {
        "customer_email": customer_email,
        "expires_at": expires_at,
        "features": features,
        "issued_at": issued_at,
        "license_key": license_key,
        "machine_fingerprint": machine_fingerprint,
    }
    signable_bytes = json.dumps(
        signable, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    signature = _sign(signable_bytes, private_seed)

    return {
        "license_key": license_key,
        "customer_email": customer_email,
        "machine_fingerprint": machine_fingerprint,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "features": features,
        "signature": signature,
    }


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry-point for the keygen CLI."""
    parser = argparse.ArgumentParser(
        description="Ed25519 license keygen and signing tool"
    )
    parser.add_argument(
        "--gen-keypair",
        action="store_true",
        help="Generate a fresh Ed25519 keypair, print to stdout, and exit",
    )
    parser.add_argument(
        "--private-key",
        help="Base64url-encoded 32-byte private-key seed (required for signing)",
    )
    parser.add_argument("--license-key", help="License key string")
    parser.add_argument("--email", help="Customer e-mail address")
    parser.add_argument("--fingerprint", help="Machine fingerprint (cpu:mb:guid)")
    parser.add_argument(
        "--expires",
        default=None,
        help="Expiry datetime in ISO 8601 format, or 'none' for perpetual",
    )
    parser.add_argument(
        "--features",
        nargs="*",
        default=[],
        help="Space-separated list of feature flags",
    )
    parser.add_argument(
        "-o", "--output",
        default="license.lic",
        help="Output file path (default: license.lic)",
    )
    args = parser.parse_args()

    # ── Mode 1: keypair generation ──
    if args.gen_keypair:
        priv, pub = _generate_keypair()
        b64_priv = base64.urlsafe_b64encode(priv).decode()
        b64_pub = base64.urlsafe_b64encode(pub).decode()

        print(f"Private key (base64url): {b64_priv}")
        print(f"Public  key (base64url): {b64_pub}")
        print()
        print("# Paste into license_crypto.py as _EMBEDDED_PUBLIC_KEY:")
        print("_EMBEDDED_PUBLIC_KEY: bytes = (")
        for i in range(0, len(pub), 8):
            chunk = pub[i : i + 8]
            lit = "".join(f"\\x{b:02x}" for b in chunk)
            print(f'    b"{lit}"')
        print(")")
        return

    # ── Mode 2: sign a license ──
    required = {
        "--private-key": args.private_key,
        "--license-key": args.license_key,
        "--email": args.email,
        "--fingerprint": args.fingerprint,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")

    private_seed = base64.urlsafe_b64decode(args.private_key)
    if len(private_seed) != 32:
        print(
            "Error: --private-key must decode to exactly 32 bytes",
            file=sys.stderr,
        )
        sys.exit(1)

    expires_at: str | None = (
        None if args.expires in (None, "none", "None") else args.expires
    )

    license_dict = _build_license(
        license_key=args.license_key,
        customer_email=args.email,
        machine_fingerprint=args.fingerprint,
        expires_at=expires_at,
        features=args.features,
        private_seed=private_seed,
    )

    # Verify the signature we just created (sanity check)
    pub_seed = Ed25519PrivateKey.from_private_bytes(private_seed)
    pub_bytes = pub_seed.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    signable = {
        "customer_email": license_dict["customer_email"],
        "expires_at": license_dict["expires_at"],
        "features": license_dict["features"],
        "issued_at": license_dict["issued_at"],
        "license_key": license_dict["license_key"],
        "machine_fingerprint": license_dict["machine_fingerprint"],
    }
    signable_bytes = json.dumps(
        signable, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if not _verify(signable_bytes, str(license_dict["signature"]), pub_bytes):
        print("FATAL: self-verification of signature failed", file=sys.stderr)
        sys.exit(2)

    license_json = json.dumps(license_dict, indent=2)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(license_json)

    print(f"License written to: {args.output}")
    print(f"Signature verified: OK")


if __name__ == "__main__":
    main()

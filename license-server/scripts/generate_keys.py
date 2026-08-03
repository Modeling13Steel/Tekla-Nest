#!/usr/bin/env python3
"""Generate RSA key pair for JWT signing.

Outputs:
  keys/private_key.pem  — keep SECRET, upload to Firebase Secret Manager
  keys/public_key.pem   — embed in the client application

Usage:
    python scripts/generate_keys.py
"""
from pathlib import Path
import os

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def main() -> None:
    keys_dir = Path(__file__).resolve().parent.parent / "keys"
    keys_dir.mkdir(exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    priv_path = keys_dir / "private_key.pem"
    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(priv_path, 0o600)
    print(f"Private key → {priv_path}")

    pub_path = keys_dir / "public_key.pem"
    pub_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Public key  → {pub_path}")

    # Copy public key to client SDK
    client_key = (
        Path(__file__).resolve().parent.parent.parent
        / "src" / "tekla_nest" / "licensing" / "public_key.pem"
    )
    client_key.parent.mkdir(parents=True, exist_ok=True)
    client_key.write_bytes(pub_path.read_bytes())
    print(f"Public key copied → {client_key}")

    print(
        "\nNext steps:\n"
        "  1. Upload private key with Firebase Functions secrets:\n"
        "     firebase functions:secrets:set JWT_PRIVATE_KEY < keys/private_key.pem\n"
        "  2. Upload an admin API key:\n"
        "     ADMIN_KEY=$(openssl rand -hex 32); echo \"$ADMIN_KEY\"\n"
        "     printf \"%s\" \"$ADMIN_KEY\" | firebase functions:secrets:set ADMIN_API_KEY\n"
        "  3. Upload a break-glass master admin key and store it offline:\n"
        "     MASTER_ADMIN_KEY=$(openssl rand -hex 48); echo \"$MASTER_ADMIN_KEY\"\n"
        "     printf \"%s\" \"$MASTER_ADMIN_KEY\" | "
        "firebase functions:secrets:set MASTER_ADMIN_API_KEY\n"
        "  4. Create the Firebase Functions venv:\n"
        "     python3.12 scripts/bootstrap_functions_venv.py\n"
        "  5. Deploy: firebase deploy --only functions"
    )


if __name__ == "__main__":
    main()

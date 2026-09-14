"""License file schema and result types."""

from __future__ import annotations

import dataclasses
import json
from typing import TypeVar

T = TypeVar("T")


@dataclasses.dataclass(slots=True)
class LicenseFile:
    """Signed license file stored on disk."""

    license_key: str
    customer_email: str
    machine_fingerprint: str
    issued_at: str
    expires_at: str | None
    features: list[str]
    signature: str

    def signable_bytes(self) -> bytes:
        """Return canonical UTF-8 JSON of all fields except *signature*."""
        payload = {
            "customer_email": self.customer_email,
            "expires_at": self.expires_at,
            "features": self.features,
            "issued_at": self.issued_at,
            "license_key": self.license_key,
            "machine_fingerprint": self.machine_fingerprint,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def to_json(self) -> str:
        """Serialize the full license to a pretty-printed JSON string."""
        return json.dumps(dataclasses.asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> LicenseFile:
        """Deserialize from a JSON string.  Raises *KeyError* / *ValueError*."""
        data: dict = json.loads(text)
        return cls(
            license_key=data["license_key"],
            customer_email=data["customer_email"],
            machine_fingerprint=data["machine_fingerprint"],
            issued_at=data["issued_at"],
            expires_at=data.get("expires_at"),
            features=data.get("features", []),
            signature=data["signature"],
        )


@dataclasses.dataclass(slots=True)
class Ok:
    """Success result wrapping a value of type *T*."""

    value: T


@dataclasses.dataclass(slots=True)
class Err:
    """Failure result wrapping an error message."""

    error: str

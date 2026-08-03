"""Typed admin-license records shared by the admin API client and GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def parse_datetime(value: object) -> datetime | None:
    """Parse ISO-like datetimes returned by Firebase Functions."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def format_datetime(value: datetime | None) -> str:
    """Return a compact human-readable timestamp for admin tables."""
    if value is None:
        return "-"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


@dataclass(frozen=True)
class LicenseRecord:
    license_key: str
    customer: str
    created_at: datetime | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    machines: list[str] = field(default_factory=list)
    max_machines: int = 1
    revoked: bool = False
    last_validated: datetime | None = None
    days_remaining: int | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> LicenseRecord:
        machines = data.get("machines", [])
        if not isinstance(machines, list):
            machines = []
        return cls(
            license_key=str(data.get("license_key") or ""),
            customer=str(data.get("customer") or ""),
            created_at=parse_datetime(data.get("created_at")),
            activated_at=parse_datetime(data.get("activated_at")),
            expires_at=parse_datetime(data.get("expires_at")),
            machines=[str(machine) for machine in machines],
            max_machines=_positive_int(data.get("max_machines"), 1),
            revoked=bool(data.get("revoked", False)),
            last_validated=parse_datetime(data.get("last_validated")),
            days_remaining=_optional_int(data.get("days_remaining")),
        )

    @property
    def machine_count(self) -> int:
        return len(self.machines)

    @property
    def machine_usage(self) -> str:
        return f"{self.machine_count}/{self.max_machines}"

    def status(self, now: datetime | None = None) -> str:
        if self.revoked:
            return "revoked"
        current = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at and expires_at < current:
            return "expired"
        if self.machine_count == 0:
            return "unactivated"
        if self.machine_count >= self.max_machines:
            return "full"
        return "active"


@dataclass(frozen=True)
class CreateLicenseRequest:
    customer: str
    duration_days: int
    max_machines: int


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


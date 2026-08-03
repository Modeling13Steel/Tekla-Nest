"""Allowlisted report-preview command parsing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QUrl


class ReportActionError(ValueError):
    """Raised when a report preview command is malformed or stale."""


@dataclass(frozen=True)
class ReportReorderCommand:
    profile_index: int
    bar_row: int
    direction: int

    @property
    def new_row(self) -> int:
        return self.bar_row + self.direction


def parse_reorder_url(
    url: QUrl | str,
    bar_counts: Sequence[int] | None = None,
) -> ReportReorderCommand:
    """Parse and validate ``reorder:///profile/bar/direction`` URLs."""
    qurl = QUrl(url) if isinstance(url, str) else url
    if qurl.scheme() != "reorder":
        raise ReportActionError("Unsupported report command.")

    parts: list[str] = []
    if qurl.authority():
        parts.append(_numeric_authority(qurl.authority()))
    path = qurl.path().strip("/")
    if path:
        parts.extend(path.split("/"))

    if len(parts) != 3:
        raise ReportActionError("Malformed reorder command.")

    try:
        profile_index, bar_row, direction = (int(part) for part in parts)
    except ValueError as exc:
        raise ReportActionError("Reorder command values must be integers.") from exc

    if profile_index < 0 or bar_row < 0:
        raise ReportActionError("Reorder command target is out of range.")
    if direction not in (-1, 1):
        raise ReportActionError("Reorder direction must be up or down.")

    command = ReportReorderCommand(profile_index, bar_row, direction)
    if bar_counts is not None:
        if profile_index >= len(bar_counts):
            raise ReportActionError("Reorder command refers to a stale profile.")
        bar_count = bar_counts[profile_index]
        if bar_row >= bar_count or not 0 <= command.new_row < bar_count:
            raise ReportActionError("Reorder command refers to a stale bar.")

    return command


def _numeric_authority(authority: str) -> str:
    host = authority.split("@")[-1].split(":")[0]
    octets = host.split(".")
    if len(octets) == 4 and octets[:3] == ["0", "0", "0"] and octets[3].isdigit():
        return octets[3]
    return host

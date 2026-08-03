"""Provider backed by an in-memory list (for manual table entry)."""
from __future__ import annotations

from ..models import PartEntry
from .base_provider import PartProvider


class ManualPartProvider(PartProvider):
    """Stores parts added manually through the GUI."""

    def __init__(self) -> None:
        self._parts: list[PartEntry] = []

    def set_parts(self, parts: list[PartEntry]) -> None:
        """Replace the internal list with a copy of *parts*."""
        self._parts = list(parts)

    def add_part(self, part: PartEntry) -> None:
        """Append a single part entry."""
        self._parts.append(part)

    def clear(self) -> None:
        """Remove all entries."""
        self._parts.clear()

    def get_parts(self) -> list[PartEntry]:
        return list(self._parts)

"""Abstract interface for part data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import PartEntry


class PartProvider(ABC):
    """A pluggable source of part entries for nesting."""

    @abstractmethod
    def get_parts(self) -> list[PartEntry]:
        """Return a list of grouped part entries."""
        ...

"""Provider that wraps csv_loader to implement the PartProvider interface."""
from __future__ import annotations

from pathlib import Path

from ..models import PartEntry
from ..services.csv_loader import load_parts_csv
from .base_provider import PartProvider


class CsvPartProvider(PartProvider):
    """Loads parts from a CSV file."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def get_parts(self) -> list[PartEntry]:
        return load_parts_csv(self._path)

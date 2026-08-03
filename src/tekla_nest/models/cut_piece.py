from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CutPiece:
    """A single desired cut (one piece, not grouped).

    Migrated from: C# Part class in FrmNest.cs
    """

    length: float  # mm
    mark: str  # part reference, e.g. "15C1"


@dataclass
class PartEntry:
    """A grouped part entry as shown in the parts table (with quantity).

    Migrated from: C# PecaCorte class in FrmNest.cs
    """

    quantity: int
    length: float  # mm
    reference: str  # part mark
    profile: str  # e.g. "HEA240"
    material: str  # e.g. "S275JR"

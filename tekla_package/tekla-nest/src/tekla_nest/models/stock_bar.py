from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StockBar:
    """An available stock bar (a single physical bar, expanded from quantity).

    Migrated from: C# propriedadedebarra class in FrmNest.cs

    The ``priority`` field carries the source-priority forward into the
    optimizer so client stock (priority < 0) is consumed before market
    stock regardless of which length-sorting strategy is being tried.
    Lower priority values are consumed first.
    """

    length: float  # mm
    mark: str  # bar reference / profile name
    material: str  # steel grade
    source: str  # "Cliente" or "Mercado"
    priority: int = 0


@dataclass
class StockEntry:
    """A grouped stock entry as shown in the stock table (with quantity).

    Migrated from: C# StockItemModel + propriedadedebarra
    """

    quantity: int
    length: float  # mm
    priority: int  # lower = use first; client stock gets -1000
    profile: str
    material: str
    source: str = "Mercado"

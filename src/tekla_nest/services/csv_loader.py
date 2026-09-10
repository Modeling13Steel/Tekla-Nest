"""CSV import/export for stock and part data.

Migrated from: C# FrmNest.loadStockFromCSVToolStripMenuItem_Click + StockItemModel parsing.
Handles both ';' and ',' separators with auto-detection.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from ..config.app_config import get_config
from ..models import PartEntry, StockEntry

LOGGER = logging.getLogger(__name__)


def _log(msg: str) -> None:
    """Diagnostic trace for CSV import/export, gated behind DEBUG logging."""
    LOGGER.debug(msg)


class CsvError(Exception):
    """Raised when a CSV file cannot be parsed.

    Messages include the file path, line number (when available),
    and what was expected.
    """


def load_stock_csv(path: Path | str) -> list[StockEntry]:
    """Load stock entries from a CSV file.

    Expected columns (case-insensitive):
        Quantidade, comprimento, prioridade, perfil, material

    Separator: auto-detected from config (';' or ',')

    Args:
        path: Path to the CSV file.

    Returns:
        List of StockEntry with source="Cliente".

    Raises:
        CsvError: If the file is missing, empty, or has wrong columns.
    """
    path = Path(path)
    _log(f"load_stock_csv START  path={path}  exists={path.exists()}  size={path.stat().st_size if path.exists() else 'N/A'}")
    _check_file(path)
    _log("load_stock_csv file check passed")

    text = _read_text(path)
    _log(f"load_stock_csv text read  len={len(text)}  first_line={text.splitlines()[0][:120] if text else '<empty>'!r}")
    sep = _detect_separator(text, get_config().csv_separators)
    _log(f"load_stock_csv separator={sep!r}")
    reader = csv.DictReader(text.splitlines(), delimiter=sep)

    if reader.fieldnames:
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

    _log(f"load_stock_csv columns={list(reader.fieldnames or [])}")
    _check_columns(path, reader.fieldnames, ["quantidade", "comprimento", "perfil"])
    _log("load_stock_csv column check passed")

    entries: list[StockEntry] = []
    for line_num, row in enumerate(reader, start=2):
        try:
            quantity = int(row.get("quantidade", "0"))
            length = float(row.get("comprimento", "0"))
            priority = int(row.get("prioridade", "0") or "0")
            profile = row.get("perfil", "").strip()
            material = row.get("material", "").strip()

            if quantity > 0 and length > 0 and profile:
                entries.append(StockEntry(
                    quantity=quantity,
                    length=length,
                    priority=priority,
                    profile=profile,
                    material=material,
                    source="Cliente",
                ))
        except (ValueError, TypeError) as exc:
            _log(f"load_stock_csv ROW ERROR  line={line_num}  row={dict(row)}  exc={exc}")
            raise CsvError(
                f"CSV '{path.name}' line {line_num}: cannot parse row — {exc}\n"
                f"  Expected: quantidade=int, comprimento=float, prioridade=int"
            ) from exc

    _log(f"load_stock_csv END  entries={len(entries)}")
    return entries


def load_parts_csv(path: Path | str) -> list[PartEntry]:
    """Load part entries from a CSV file.

    Expected columns (case-insensitive):
        quantidade, comprimento, referencia, perfil, material

    Args:
        path: Path to the CSV file.

    Returns:
        List of PartEntry.

    Raises:
        CsvError: If the file is missing, empty, or has wrong columns.
    """
    path = Path(path)
    _log(f"load_parts_csv START  path={path}  exists={path.exists()}  size={path.stat().st_size if path.exists() else 'N/A'}")
    _check_file(path)
    _log("load_parts_csv file check passed")

    text = _read_text(path)
    _log(f"load_parts_csv text read  len={len(text)}  first_line={text.splitlines()[0][:120] if text else '<empty>'!r}")
    sep = _detect_separator(text, get_config().csv_separators)
    _log(f"load_parts_csv separator={sep!r}")
    reader = csv.DictReader(text.splitlines(), delimiter=sep)

    if reader.fieldnames:
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

    _log(f"load_parts_csv columns={list(reader.fieldnames or [])}")
    _check_columns(path, reader.fieldnames, ["quantidade", "comprimento", "perfil"])
    _log("load_parts_csv column check passed")

    entries: list[PartEntry] = []
    for line_num, row in enumerate(reader, start=2):
        try:
            entries.append(PartEntry(
                quantity=int(row.get("quantidade", "0")),
                length=float(row.get("comprimento", "0")),
                reference=row.get("referencia", "").strip(),
                profile=row.get("perfil", "").strip(),
                material=row.get("material", "").strip(),
            ))
        except (ValueError, TypeError) as exc:
            _log(f"load_parts_csv ROW ERROR  line={line_num}  row={dict(row)}  exc={exc}")
            raise CsvError(
                f"CSV '{path.name}' line {line_num}: cannot parse row — {exc}\n"
                f"  Expected: quantidade=int, comprimento=float"
            ) from exc

    _log(f"load_parts_csv END  entries={len(entries)}")
    return entries


def export_stock_csv(entries: list[StockEntry], path: Path | str) -> None:
    """Export stock entries to a CSV file.

    Args:
        entries: Stock entries to export.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Quantidade", "comprimento", "prioridade", "perfil", "material"])
        for e in entries:
            writer.writerow([e.quantity, e.length, e.priority, e.profile, e.material])


def export_parts_csv(entries: list[PartEntry], path: Path | str) -> None:
    """Export part entries to a CSV file.

    Args:
        entries: Part entries to export.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Quantidade", "comprimento", "referencia", "perfil", "material"])
        for e in entries:
            writer.writerow([e.quantity, e.length, e.reference, e.profile, e.material])


# ── Private helpers ──────────────────────────────────────────


def _check_file(path: Path) -> None:
    """Validate that the file exists and is readable."""
    if not path.exists():
        raise CsvError(
            f"CSV file not found: '{path}'\n"
            f"  Fix: Check the file path. The file must exist before loading."
        )
    if not path.is_file():
        raise CsvError(
            f"CSV path is not a file: '{path}'\n"
            f"  Fix: Provide a path to a .csv file, not a directory."
        )


_ENCODING_CANDIDATES = ("utf-8-sig", "utf-16", "cp1252", "latin-1")


def _read_text(path: Path) -> str:
    """Read file text with encoding fallbacks for common Excel exports.

    Tries UTF-8 (with BOM), then UTF-16 (Excel "Unicode Text"), then
    Windows-1252 (default on PT Excel), then Latin-1 (last resort).
    Also strips Excel's ``sep=<x>`` prefix line if present.
    """
    raw = path.read_bytes()
    _log(f"_read_text  raw_bytes={len(raw)}  bom={raw[:4].hex()}")
    last_err: UnicodeDecodeError | None = None
    text: str | None = None
    for encoding in _ENCODING_CANDIDATES:
        try:
            text = raw.decode(encoding)
            _log(f"_read_text  encoding={encoding!r} OK")
            break
        except UnicodeDecodeError as exc:
            _log(f"_read_text  encoding={encoding!r} FAILED: {exc}")
            last_err = exc
    if text is None:
        _log("_read_text  ALL ENCODINGS FAILED")
        raise CsvError(
            f"CSV '{path.name}' could not be decoded with any supported encoding.\n"
            f"  Detail: {last_err}\n"
            f"  Fix: Re-save the file as UTF-8 from Excel "
            f"(File → Save As → 'CSV UTF-8')."
        ) from last_err
    text = text.lstrip("\ufeff")
    first_nl = text.find("\n")
    if first_nl != -1:
        first = text[:first_nl].strip().lower()
        if first.startswith("sep="):
            text = text[first_nl + 1 :]
    return text


def _check_columns(
    path: Path,
    actual: list | None,
    required: list[str],
) -> None:
    """Check that required columns are present."""
    if not actual:
        raise CsvError(
            f"CSV '{path.name}' appears to be empty (no header row found).\n"
            f"  Expected columns: {', '.join(required)}"
        )
    missing = [c for c in required if c not in actual]
    if missing:
        raise CsvError(
            f"CSV '{path.name}' is missing required columns: {missing}\n"
            f"  Found columns: {list(actual)}\n"
            f"  Expected (case-insensitive): {required}"
        )


def _detect_separator(text: str, candidates: list[str]) -> str:
    """Auto-detect CSV separator from the header line.

    Counts occurrences of each candidate on the first line and picks the
    most frequent. Ties are broken by candidate order.
    """
    first_line = text.split("\n", 1)[0]
    best_sep = candidates[0] if candidates else ","
    best_count = -1
    for sep in candidates:
        count = first_line.count(sep)
        if count > best_count:
            best_count = count
            best_sep = sep
    if best_count <= 0:
        return candidates[0] if candidates else ","
    return best_sep

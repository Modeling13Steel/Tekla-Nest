"""F20 — CSV import must tolerate real-world Excel encodings.

Regression for user-reported failure: a file with header
``quantidade;comprimento;perfil;material;referencia`` and a single row
``1;19000;WI300-15-20*300;Steel_Undefined;b/0(?)`` failed to load when
saved from Portuguese Windows Excel.

Pinned scenarios:

1. Plain UTF-8 with ``;`` (the original user payload)
2. Same payload comma-separated (default-comma policy)
3. UTF-8 + BOM
4. UTF-16 LE + BOM (Excel "Unicode Text")
5. Windows-1252 / Latin-1 with an accented optional column
6. Excel ``sep=;`` prefix line
"""

from __future__ import annotations

import codecs
from pathlib import Path

import pytest

from tekla_nest.services.csv_loader import load_parts_csv

USER_HEADER_SEMI = "quantidade;comprimento;perfil;material;referencia"
USER_ROW_SEMI = "1;19000;WI300-15-20*300;Steel_Undefined;b/0(?)"


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _assert_user_row(entries: list) -> None:
    assert len(entries) == 1
    e = entries[0]
    assert e.quantity == 1
    assert e.length == pytest.approx(19000.0)
    assert e.profile == "WI300-15-20*300"
    assert e.material == "Steel_Undefined"
    assert e.reference == "b/0(?)"


class TestF20UserReportedCsv:
    """Pin the exact user payload + Excel-export encoding variants."""

    def test_user_payload_utf8_semicolon(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "user.csv",
            f"{USER_HEADER_SEMI}\n{USER_ROW_SEMI}\n".encode(),
        )
        _assert_user_row(load_parts_csv(path))

    def test_user_payload_utf8_comma(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "user_comma.csv",
            (
                b"quantidade,comprimento,perfil,material,referencia\n"
                b"1,19000,WI300-15-20*300,Steel_Undefined,b/0(?)\n"
            ),
        )
        _assert_user_row(load_parts_csv(path))

    def test_utf8_bom(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "bom.csv",
            codecs.BOM_UTF8 + f"{USER_HEADER_SEMI}\n{USER_ROW_SEMI}\n".encode(),
        )
        _assert_user_row(load_parts_csv(path))

    def test_utf16_le_excel_unicode_text(self, tmp_path: Path) -> None:
        body = f"{USER_HEADER_SEMI}\n{USER_ROW_SEMI}\n".encode("utf-16-le")
        path = _write(tmp_path, "utf16.csv", codecs.BOM_UTF16_LE + body)
        _assert_user_row(load_parts_csv(path))

    def test_windows1252_accented_optional_header(self, tmp_path: Path) -> None:
        body = (
            "quantidade;comprimento;perfil;material;referência\n"
            "1;19000;WI300-15-20*300;Steel_Undefined;b/0(?)\n"
        ).encode("cp1252")
        path = _write(tmp_path, "pt_excel.csv", body)
        entries = load_parts_csv(path)
        assert len(entries) == 1
        assert entries[0].quantity == 1
        assert entries[0].length == pytest.approx(19000.0)
        assert entries[0].profile == "WI300-15-20*300"

    def test_excel_sep_prefix_line(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "sepprefix.csv",
            f"sep=;\n{USER_HEADER_SEMI}\n{USER_ROW_SEMI}\n".encode(),
        )
        _assert_user_row(load_parts_csv(path))

    def test_separator_detection_picks_majority(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mixed.csv",
            (
                b"quantidade;comprimento;perfil;material;referencia\n"
                b"1;19000;WI300-15-20*300;Steel_Undefined;a,b,c\n"
            ),
        )
        entries = load_parts_csv(path)
        assert len(entries) == 1
        assert entries[0].reference == "a,b,c"

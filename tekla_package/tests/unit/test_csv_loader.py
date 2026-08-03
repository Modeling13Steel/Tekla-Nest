"""Unit tests for csv_loader service."""

from __future__ import annotations

import pytest
from tekla_common.config.app_config import load_config, reset_config
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.services.csv_loader import (
    CsvError,
    export_parts_csv,
    export_stock_csv,
    load_parts_csv,
    load_stock_csv,
)


@pytest.fixture(autouse=True)
def _reset_cfg():
    reset_config()
    load_config()
    yield
    reset_config()


# ── load_stock_csv ───────────────────────────────────────────


class TestLoadStockCsv:
    def test_semicolon_separator(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n"
            "10;6100;0;HEA240;S275JR\n"
            "5;12000;1;IPE200;S355\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 2
        assert entries[0].quantity == 10
        assert entries[0].length == 6100.0
        assert entries[0].profile == "HEA240"
        assert entries[0].material == "S275JR"
        assert entries[0].source == "Cliente"

    def test_comma_separator(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade,comprimento,prioridade,perfil,material\n3,8000,0,UPN200,S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 1
        assert entries[0].quantity == 3
        assert entries[0].length == 8000.0

    def test_case_insensitive_headers(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "QUANTIDADE;COMPRIMENTO;PRIORIDADE;PERFIL;MATERIAL\n2;10000;0;HEB300;S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 1

    def test_utf8_bom(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_bytes(
            b"\xef\xbb\xbf"  # UTF-8 BOM
            b"Quantidade;comprimento;prioridade;perfil;material\n"
            b"1;6000;0;HEA;S275\n"
        )
        entries = load_stock_csv(f)
        assert len(entries) == 1

    def test_skips_zero_quantity(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n"
            "0;6100;0;HEA240;S275\n"
            "5;6100;0;HEA240;S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 1

    def test_skips_zero_length(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n5;0;0;HEA240;S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 0

    def test_skips_empty_profile(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n5;6000;0;;S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 0

    def test_missing_file_raises(self):
        with pytest.raises(CsvError, match="not found"):
            load_stock_csv("/tmp/nonexistent_file_xyz.csv")

    def test_directory_path_raises(self, tmp_path):
        with pytest.raises(CsvError, match="not a file"):
            load_stock_csv(tmp_path)

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("", encoding="utf-8")
        with pytest.raises(CsvError, match="empty"):
            load_stock_csv(f)

    def test_missing_columns_raises(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("col_a;col_b\n1;2\n", encoding="utf-8")
        with pytest.raises(CsvError, match="missing required columns"):
            load_stock_csv(f)

    def test_bad_value_raises(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\nnot_a_number;6000;0;HEA;S275\n",
            encoding="utf-8",
        )
        with pytest.raises(CsvError, match="line 2.*cannot parse"):
            load_stock_csv(f)

    def test_optional_prioridade_defaults_to_zero(self, tmp_path):
        f = tmp_path / "stock.csv"
        f.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n5;6000;;HEA240;S275\n",
            encoding="utf-8",
        )
        entries = load_stock_csv(f)
        assert len(entries) == 1
        assert entries[0].priority == 0


# ── load_parts_csv ───────────────────────────────────────────


class TestLoadPartsCsv:
    def test_basic_load(self, tmp_path):
        f = tmp_path / "parts.csv"
        f.write_text(
            "Quantidade;comprimento;referencia;perfil;material\n"
            "3;2500;C1;HEA240;S275JR\n"
            "1;4000;D2;IPE200;S355\n",
            encoding="utf-8",
        )
        entries = load_parts_csv(f)
        assert len(entries) == 2
        assert entries[0].quantity == 3
        assert entries[0].length == 2500.0
        assert entries[0].reference == "C1"
        assert entries[0].profile == "HEA240"
        assert entries[0].material == "S275JR"

    def test_missing_file_raises(self):
        with pytest.raises(CsvError, match="not found"):
            load_parts_csv("/tmp/nonexistent_xyz.csv")


# ── export_stock_csv ─────────────────────────────────────────


class TestExportStockCsv:
    def test_round_trip(self, tmp_path):
        original = [
            StockEntry(quantity=10, length=6100, priority=0, profile="HEA240", material="S275JR"),
            StockEntry(quantity=5, length=12000, priority=1, profile="IPE200", material="S355"),
        ]
        out_path = tmp_path / "exported.csv"
        export_stock_csv(original, out_path)
        reloaded = load_stock_csv(out_path)

        assert len(reloaded) == len(original)
        for orig, rel in zip(original, reloaded, strict=False):
            assert rel.quantity == orig.quantity
            assert rel.length == pytest.approx(orig.length)
            assert rel.priority == orig.priority
            assert rel.profile == orig.profile
            assert rel.material == orig.material

    def test_creates_parent_dirs(self, tmp_path):
        out_path = tmp_path / "sub" / "dir" / "stock.csv"
        export_stock_csv([], out_path)
        assert out_path.exists()


# ── export_parts_csv ─────────────────────────────────────────


class TestExportPartsCsv:
    def test_round_trip(self, tmp_path):
        original = [
            PartEntry(quantity=2, length=3000, reference="A1", profile="HEA240", material="S275"),
        ]
        out_path = tmp_path / "parts.csv"
        export_parts_csv(original, out_path)
        reloaded = load_parts_csv(out_path)

        assert len(reloaded) == 1
        assert reloaded[0].quantity == 2
        assert reloaded[0].length == pytest.approx(3000.0)
        assert reloaded[0].reference == "A1"
        assert reloaded[0].profile == "HEA240"

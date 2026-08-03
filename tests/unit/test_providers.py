"""Unit tests for data providers."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.models import PartEntry
from tekla_nest.providers import (
    CsvPartProvider,
    ManualPartProvider,
    PartProvider,
    TeklaPartProvider,
)


@pytest.fixture(autouse=True)
def _reset_cfg():
    reset_config()
    load_config()
    yield
    reset_config()


# ── ManualPartProvider ───────────────────────────────────────


class TestManualPartProvider:
    def test_empty_by_default(self):
        p = ManualPartProvider()
        assert p.get_parts() == []

    def test_set_parts(self):
        p = ManualPartProvider()
        entries = [PartEntry(2, 3000, "A1", "HEA240", "S275")]
        p.set_parts(entries)
        assert len(p.get_parts()) == 1
        assert p.get_parts()[0].reference == "A1"

    def test_set_parts_copies(self):
        p = ManualPartProvider()
        entries = [PartEntry(1, 1000, "X", "IPE200", "S355")]
        p.set_parts(entries)
        entries.clear()  # mutate original
        assert len(p.get_parts()) == 1  # provider unaffected

    def test_get_parts_returns_copy(self):
        p = ManualPartProvider()
        p.set_parts([PartEntry(1, 1000, "X", "IPE200", "S355")])
        result = p.get_parts()
        result.clear()
        assert len(p.get_parts()) == 1  # internal list unaffected

    def test_add_part(self):
        p = ManualPartProvider()
        p.add_part(PartEntry(1, 1000, "A", "HEA", "S275"))
        p.add_part(PartEntry(2, 2000, "B", "IPE", "S355"))
        assert len(p.get_parts()) == 2

    def test_clear(self):
        p = ManualPartProvider()
        p.set_parts([PartEntry(1, 1000, "X", "IPE200", "S355")])
        p.clear()
        assert p.get_parts() == []

    def test_is_part_provider(self):
        assert isinstance(ManualPartProvider(), PartProvider)


# ── CsvPartProvider ──────────────────────────────────────────


class TestCsvPartProvider:
    def test_loads_csv_file(self, tmp_path):
        f = tmp_path / "parts.csv"
        f.write_text(
            "Quantidade;comprimento;referencia;perfil;material\n"
            "3;2500;C1;HEA240;S275JR\n"
            "1;4000;D2;IPE200;S355\n",
            encoding="utf-8",
        )
        p = CsvPartProvider(f)
        parts = p.get_parts()
        assert len(parts) == 2
        assert parts[0].quantity == 3
        assert parts[0].reference == "C1"

    def test_missing_file_raises(self):
        p = CsvPartProvider("/tmp/nonexistent_xyz_provider.csv")
        with pytest.raises(Exception, match="not found"):
            p.get_parts()

    def test_is_part_provider(self, tmp_path):
        assert isinstance(CsvPartProvider(tmp_path / "x.csv"), PartProvider)


# ── TeklaPartProvider ───────────────────────────────────────


class TestTeklaPartProvider:
    @staticmethod
    def _make_obj(properties: dict[str, object]):
        """Fake Tekla model object with GetReportProperty matching the .NET API."""
        class FakeTeklaObject:
            def __init__(self, props: dict[str, object]):
                self._props = props

            def GetReportProperty(self, name: str, default):
                if name in self._props:
                    return True, self._props[name]
                return False, default

        return FakeTeklaObject(properties)

    def test_no_tekla_found_raises(self):
        """When no Tekla installation can be found, raise RuntimeError."""
        with patch("tekla_nest.services.tekla_api.find_tekla_bin", return_value=None):
            p = TeklaPartProvider()
            with pytest.raises(RuntimeError, match="Could not find Tekla"):
                p.get_parts()

    def test_filters_plates(self):
        """Objects with PL or CHA in profile are excluded."""
        bar = self._make_obj(
            {"PROFILE": "HEA240", "MATERIAL": "S275", "PART_POS": "A1", "LENGTH": 3000.0}
        )
        plate = self._make_obj(
            {"PROFILE": "PL20", "MATERIAL": "S275", "PART_POS": "P1", "LENGTH": 500.0}
        )
        chapa = self._make_obj(
            {"PROFILE": "CHA100", "MATERIAL": "S275", "PART_POS": "C1", "LENGTH": 200.0}
        )

        with patch("tekla_nest.services.tekla_api.find_tekla_bin", return_value=r"C:\Tekla\bin"):
            with patch("tekla_nest.services.tekla_api.load_tekla_assemblies"):
                with patch("tekla_nest.services.tekla_api.connect_model"):
                    with patch("tekla_nest.services.tekla_api.get_selected_objects", return_value=iter([bar, plate, chapa])):
                        parts = TeklaPartProvider().get_parts()

        assert len(parts) == 1
        assert parts[0].profile == "HEA240"
        assert parts[0].reference == "A1"

    def test_groups_by_reference(self):
        """Multiple objects with same PART_POS are grouped and counted."""
        objects = [
            self._make_obj({"PROFILE": "HEA240", "MATERIAL": "S275", "PART_POS": "A1", "LENGTH": 3000.0}),
            self._make_obj({"PROFILE": "HEA240", "MATERIAL": "S275", "PART_POS": "A1", "LENGTH": 3000.0}),
            self._make_obj({"PROFILE": "HEA240", "MATERIAL": "S275", "PART_POS": "B1", "LENGTH": 5000.0}),
        ]

        with patch("tekla_nest.services.tekla_api.find_tekla_bin", return_value=r"C:\Tekla\bin"):
            with patch("tekla_nest.services.tekla_api.load_tekla_assemblies"):
                with patch("tekla_nest.services.tekla_api.connect_model"):
                    with patch("tekla_nest.services.tekla_api.get_selected_objects", return_value=iter(objects)):
                        parts = TeklaPartProvider().get_parts()

        assert len(parts) == 2
        a1 = next(p for p in parts if p.reference == "A1")
        b1 = next(p for p in parts if p.reference == "B1")
        assert a1.quantity == 2
        assert b1.quantity == 1

    def test_empty_selection(self):
        """No selection returns empty list."""
        with patch("tekla_nest.services.tekla_api.find_tekla_bin", return_value=r"C:\Tekla\bin"):
            with patch("tekla_nest.services.tekla_api.load_tekla_assemblies"):
                with patch("tekla_nest.services.tekla_api.connect_model"):
                    with patch("tekla_nest.services.tekla_api.get_selected_objects", return_value=iter([])):
                        parts = TeklaPartProvider().get_parts()

        assert parts == []

    def test_filters_blank_parts(self):
        """Objects with no profile, no reference, or zero length are excluded."""
        valid = self._make_obj(
            {"PROFILE": "HEA240", "MATERIAL": "S275", "PART_POS": "A1", "LENGTH": 3000.0}
        )
        blank = self._make_obj(
            {"PROFILE": "", "MATERIAL": "", "PART_POS": "", "LENGTH": 0.0}
        )
        no_ref = self._make_obj(
            {"PROFILE": "IPE200", "MATERIAL": "S275", "PART_POS": "", "LENGTH": 2000.0}
        )
        zero_len = self._make_obj(
            {"PROFILE": "IPE200", "MATERIAL": "S275", "PART_POS": "B1", "LENGTH": 0.0}
        )

        with patch("tekla_nest.services.tekla_api.find_tekla_bin", return_value=r"C:\Tekla\bin"):
            with patch("tekla_nest.services.tekla_api.load_tekla_assemblies"):
                with patch("tekla_nest.services.tekla_api.connect_model"):
                    with patch("tekla_nest.services.tekla_api.get_selected_objects", return_value=iter([valid, blank, no_ref, zero_len])):
                        parts = TeklaPartProvider().get_parts()

        assert len(parts) == 1
        assert parts[0].reference == "A1"

    def test_is_part_provider(self):
        assert isinstance(TeklaPartProvider(), PartProvider)

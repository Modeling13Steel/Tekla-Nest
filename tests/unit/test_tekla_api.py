"""Unit tests for the Tekla API bridge (tekla_api.py)."""
from __future__ import annotations

from unittest.mock import patch

from tekla_nest.services.tekla_api import (
    find_tekla_bin,
    get_report_property,
    resolve_tekla_bin,
)


class TestResolveTeklaBin:
    def test_none_returns_none(self):
        assert resolve_tekla_bin(None) is None

    def test_empty_string_returns_none(self):
        assert resolve_tekla_bin("") is None

    def test_nonexistent_path_returns_none(self):
        assert resolve_tekla_bin("/does/not/exist/at/all") is None

    def test_directory_returned_as_is(self, tmp_path):
        assert resolve_tekla_bin(str(tmp_path)) == str(tmp_path)

    def test_prefers_bin_subfolder(self, tmp_path):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        assert resolve_tekla_bin(str(tmp_path)) == str(bin_dir)

    def test_strips_quotes_and_whitespace(self, tmp_path):
        assert resolve_tekla_bin(f'  "{tmp_path}"  ') == str(tmp_path)

    def test_file_resolves_to_parent(self, tmp_path):
        f = tmp_path / "TeklaStructures.exe"
        f.write_text("", encoding="utf-8")
        assert resolve_tekla_bin(str(f)) == str(tmp_path)


class TestFindTeklaBin:
    def test_returns_none_on_non_windows(self):
        with patch("tekla_nest.services.tekla_api.sys") as mock_sys:
            mock_sys.platform = "darwin"
            assert find_tekla_bin() is None

    def test_env_var_detected(self, tmp_path):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        with patch("tekla_nest.services.tekla_api.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch.dict("os.environ", {"TEKLA_BIN_PATH": str(tmp_path)}, clear=False):
                with patch("tekla_nest.services.tekla_api._find_via_registry", return_value=None):
                    with patch("tekla_nest.services.tekla_api._find_via_process", return_value=None):
                        with patch("tekla_nest.services.tekla_api._find_via_filesystem", return_value=None):
                            result = find_tekla_bin()
        assert result == str(bin_dir)


class TestGetReportProperty:
    def test_found_property(self):
        obj = type("FakeObj", (), {"GetReportProperty": lambda self, n, d: (True, "HEA240")})()
        assert get_report_property(obj, "PROFILE", "") == "HEA240"

    def test_missing_property_returns_none(self):
        obj = type("FakeObj", (), {"GetReportProperty": lambda self, n, d: (False, d)})()
        assert get_report_property(obj, "NOPE", "") is None

    def test_float_property(self):
        obj = type("FakeObj", (), {"GetReportProperty": lambda self, n, d: (True, 3000.0)})()
        assert get_report_property(obj, "LENGTH", 0.0) == 3000.0

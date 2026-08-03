"""Unit tests for AppConfig loader."""
from __future__ import annotations

import pytest

from tekla_nest.config.app_config import (
    ConfigError,
    get_config,
    load_config,
    reset_config,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    yield
    reset_config()


# ── Defaults ─────────────────────────────────────────────────


class TestDefaults:
    def test_defaults_when_no_file(self):
        cfg = load_config("/tmp/nonexistent_config_67890.yaml")
        assert cfg.title == "Nest Optimizer"
        assert cfg.kerf_width == 0.0
        assert cfg.scrap_threshold == 2000.0
        assert cfg.max_strategies == 6

    def test_default_families(self):
        cfg = load_config("/tmp/nonexistent_config_67890.yaml")
        assert "HEB" in cfg.hot_rolled_families
        assert "IPE" in cfg.hot_rolled_families
        assert len(cfg.hot_rolled_families) == 7

    def test_default_lengths(self):
        cfg = load_config("/tmp/nonexistent_config_67890.yaml")
        assert 6100 in cfg.hot_rolled_lengths
        assert 12100 in cfg.hot_rolled_lengths

    def test_default_csv_separators(self):
        cfg = load_config("/tmp/nonexistent_config_67890.yaml")
        assert cfg.csv_separators == [",", ";"]


# ── YAML loading ─────────────────────────────────────────────


class TestYamlLoading:
    def test_loads_title(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("app:\n  title: My Custom Title\n", encoding="utf-8")
        cfg = load_config(str(f))
        assert cfg.title == "My Custom Title"

    def test_loads_kerf(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("nesting:\n  kerf_width: 3.5\n", encoding="utf-8")
        cfg = load_config(str(f))
        assert cfg.kerf_width == pytest.approx(3.5)

    def test_loads_theme_colors(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text(
            "theme:\n"
            "  primary_color: '#ff0000'\n"
            "  accent_color: '#00ff00'\n",
            encoding="utf-8",
        )
        cfg = load_config(str(f))
        assert cfg.primary_color == "#ff0000"
        assert cfg.accent_color == "#00ff00"

    def test_loads_stock_defaults(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text(
            "stock_defaults:\n"
            "  hot_rolled_profiles:\n"
            "    families: ['HEB', 'IPE']\n"
            "    lengths: [6000, 12000]\n"
            "    default_quantity: 50\n",
            encoding="utf-8",
        )
        cfg = load_config(str(f))
        assert cfg.hot_rolled_families == ["HEB", "IPE"]
        assert cfg.hot_rolled_lengths == [6000.0, 12000.0]
        assert cfg.default_stock_quantity == 50

    def test_loads_report_settings(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text(
            "report:\n"
            "  title: My Report\n"
            "  company_name: ACME Corp\n"
            "  show_material: false\n",
            encoding="utf-8",
        )
        cfg = load_config(str(f))
        assert cfg.report_title == "My Report"
        assert cfg.company_name == "ACME Corp"
        assert cfg.show_material is False

    def test_partial_config_keeps_defaults(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("app:\n  title: Changed\n", encoding="utf-8")
        cfg = load_config(str(f))
        assert cfg.title == "Changed"
        assert cfg.kerf_width == 0.0  # default preserved
        assert cfg.max_strategies == 6  # default preserved

    def test_empty_yaml_uses_defaults(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("", encoding="utf-8")
        cfg = load_config(str(f))
        assert cfg.title == "Nest Optimizer"

    def test_logo_path_relative_to_config(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("app:\n  logo: my_logo.png\n", encoding="utf-8")
        cfg = load_config(str(f))
        assert cfg.logo_path == tmp_path / "my_logo.png"


# ── Singleton ────────────────────────────────────────────────


class TestSingleton:
    def test_get_config_returns_same_instance(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset_clears_singleton(self):
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2

    def test_load_config_cached(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("app:\n  title: First\n", encoding="utf-8")
        load_config(str(f))
        # Second call ignores path — returns cached
        c2 = load_config("/tmp/different.yaml")
        assert c2.title == "First"


# ── Error handling ───────────────────────────────────────────


class TestConfigErrors:
    def test_invalid_yaml_syntax(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("{\n  bad yaml\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="invalid YAML"):
            load_config(str(f))

    def test_yaml_list_instead_of_dict(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("- just a list\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="must be a YAML mapping"):
            load_config(str(f))

    def test_bad_kerf_type(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("nesting:\n  kerf_width: not_a_number\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="kerf_width.*invalid value"):
            load_config(str(f))

    def test_bad_bool_type(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("report:\n  show_material: maybe\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="show_material.*invalid value"):
            load_config(str(f))

    def test_bad_section_type(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("theme: just_a_string\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="section 'theme' must be a mapping"):
            load_config(str(f))

    def test_error_message_includes_key_and_value(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("nesting:\n  max_strategies: abc\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="max_strategies.*'abc'"):
            load_config(str(f))

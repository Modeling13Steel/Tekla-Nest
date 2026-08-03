from __future__ import annotations

from tekla_common.config import app_config as _ac
from tekla_common.config.app_config import AppConfig
from tekla_common.design_system.brand import select_logo_variant
from tekla_nest.services.pdf_report import _image_mime

_RES = _ac._BASE_DIR / "resources"


def test_default_brand_assets_are_transparent_svg_first():
    cfg = AppConfig()

    assert cfg.logo_path.name == "logo_original_modern.svg"
    assert cfg.icon_path.name == "logo_cut_bar_mark.ico"
    assert cfg.report_logo_path.name == "logo_original_modern.svg"


def test_svg_logo_assets_do_not_define_white_backgrounds():
    for path in [
        (_RES / "logo_mark.svg"),
        (_RES / "logo_mark_inverse.svg"),
        (_RES / "logo_horizontal.svg"),
        (_RES / "logo_horizontal_inverse.svg"),
        (_RES / "logo_wordmark.svg"),
        (_RES / "logo_wordmark_inverse.svg"),
        (_RES / "logo_original_modern.svg"),
        (_RES / "logo_original_modern_inverse.svg"),
        (_RES / "logo_cut_bar_mark.svg"),
        (_RES / "logo_cut_bar_mark_inverse.svg"),
        (_RES / "logo_legacy.svg"),
        (_RES / "logo_legacy_inverse.svg"),
        (_RES / "logo_cut_plan.svg"),
        (_RES / "logo_grid.svg"),
    ]:
        text = path.read_text(encoding="utf-8").lower()
        assert 'fill="#ffffff"' not in text.split("<g", 1)[0]
        assert "<svg" in text
        assert "viewbox" in text


def test_report_logo_mime_supports_svg():
    assert _image_mime(_RES / "logo_original_modern.svg") == "image/svg+xml"


def test_logo_variant_switches_for_dark_backgrounds():
    assert select_logo_variant(
        (_RES / "logo_original_modern.svg"),
        "#172033",
    ) == (_RES / "logo_original_modern_inverse.svg")
    assert select_logo_variant(
        (_RES / "logo_wordmark.svg"),
        "#172033",
    ) == (_RES / "logo_wordmark_inverse.svg")


def test_logo_variant_normalizes_inverse_on_light_backgrounds():
    assert select_logo_variant(
        (_RES / "logo_original_modern_inverse.svg"),
        "#f6f8fb",
    ) == (_RES / "logo_original_modern.svg")

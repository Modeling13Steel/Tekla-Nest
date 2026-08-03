"""Feedback #8 — an image attached to the preview must persist to the
exported PDF. Previously, ``ReportPreviewWidget.set_image`` mutated only
the browser's HTML; the presenter re-rendered the report from scratch
when exporting, so the image was silently dropped.

The presenter now owns the image path and re-injects it into the
HTML right before printing.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from tekla_nest.i18n import set_language
from tekla_nest.models import (
    BarResult,
    NestResult,
    PartEntry,
    ProfileResult,
)
from tekla_nest.presenters.nest_presenter import NestPresenter


@pytest.fixture(autouse=True)
def _lang():
    set_language("en")


PNG_1X1 = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Z"
    b"k3uV0AAAAASUVORK5CYII="
)


def _png(tmp_path: Path) -> Path:
    p = tmp_path / "snap.png"
    p.write_bytes(PNG_1X1)
    return p


def _stub_result() -> NestResult:
    profile = ProfileResult(
        profile="HEA240",
        material="S275JR",
        bars=[BarResult(
            original_length=6000,
            mark="HEA240",
            material="S275JR",
            source="market",
            cuts=[3000],
            priority=0,
        )],
        unfit_pieces=[],
    )
    return NestResult(profiles=[profile])


def test_no_image_no_change(tmp_path):
    presenter = NestPresenter()
    presenter._last_result = _stub_result()
    html = "<html><body><h1>Report</h1></body></html>"
    assert presenter._inject_attached_image(html) == html


def test_image_injects_into_body(tmp_path):
    presenter = NestPresenter()
    presenter.set_attached_image(str(_png(tmp_path)))
    html = "<html><body><h1>Report</h1></body></html>"
    result = presenter._inject_attached_image(html)
    assert "report-image-wrap" in result
    assert "data:image/png;base64," in result
    # The image markup must sit BEFORE the closing body tag.
    assert result.index("data:image/png") < result.lower().rfind("</body>")


def test_missing_image_path_is_silent(tmp_path):
    presenter = NestPresenter()
    presenter.set_attached_image(str(tmp_path / "does_not_exist.png"))
    html = "<html><body>x</body></html>"
    result = presenter._inject_attached_image(html)
    assert result == html


def test_clear_parts_resets_image(tmp_path, qtbot):
    presenter = NestPresenter()
    presenter.set_parts([
        PartEntry(quantity=1, length=3000, reference="A",
                  profile="HEA240", material="S275JR")
    ])
    presenter.set_attached_image(str(_png(tmp_path)))
    presenter.clear_parts()
    assert presenter.attached_image_path() is None


def test_export_pdf_embeds_image(tmp_path, qtbot, monkeypatch):
    """The full export path: presenter renders HTML, injects image,
    prints. We intercept QTextDocument to capture the final HTML
    instead of writing a PDF.
    """
    presenter = NestPresenter()
    presenter._last_result = _stub_result()
    presenter.set_attached_image(str(_png(tmp_path)))

    captured: dict[str, str] = {}

    from PySide6.QtGui import QTextDocument

    real_set_html = QTextDocument.setHtml

    def spy_set_html(self, html):
        captured["html"] = html
        real_set_html(self, html)

    monkeypatch.setattr(QTextDocument, "setHtml", spy_set_html)

    out = tmp_path / "report.pdf"
    ok = presenter.export_pdf(str(out))
    assert ok is True
    assert "report-image-wrap" in captured["html"]
    assert "data:image/png;base64," in captured["html"]

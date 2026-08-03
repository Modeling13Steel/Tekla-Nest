"""F17 — Site image must round-trip from preview into the exported PDF.

Feedback v2 #5: the user loads an image via the report toolbar; it
appears in the in-app preview but is missing from the exported PDF.
"""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

import pytest

from tekla_nest.models import PartEntry


def _tiny_png(path: Path) -> None:
    """Write a 2x2 red PNG (no PIL dependency)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)  # 2x2, 8-bit RGB
    raw = b"\x00\xff\x00\x00\xff\x00\x00" + b"\x00\xff\x00\x00\xff\x00\x00"
    idat = zlib.compress(raw)
    path.write_bytes(
        sig + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def red_png(tmp_path):
    p = tmp_path / "site.png"
    _tiny_png(p)
    assert p.exists() and p.stat().st_size > 60
    return p


def _baseline_pdf(presenter, tmp_path) -> Path:
    out = tmp_path / "no_image.pdf"
    presenter.export_pdf(str(out))
    assert out.exists()
    return out


def _with_image_pdf(presenter, tmp_path, image_path) -> Path:
    presenter.set_attached_image(str(image_path))
    out = tmp_path / "with_image.pdf"
    presenter.export_pdf(str(out))
    assert out.exists()
    return out


def _seeded_presenter(presenter):
    presenter.set_parts([
        PartEntry(quantity=2, length=3000, reference="P1",
                  profile="IPE200", material="S275JR"),
    ])
    presenter.auto_populate_stock()
    presenter.run_optimization()
    return presenter


def test_attached_image_is_present_in_rendered_html(
    presenter, tmp_path, red_png,
):
    _seeded_presenter(presenter)
    presenter.set_attached_image(str(red_png))
    from tekla_nest.services.pdf_report import render_report_html
    html = render_report_html(
        presenter._last_result, attached_image_path=str(red_png),
    )
    assert "data:image/png;base64," in html
    assert 'class="report-image"' in html


def test_generate_report_html_includes_attached_image(presenter, red_png):
    """The preview path also includes the image — single source of truth."""
    _seeded_presenter(presenter)
    presenter.set_attached_image(str(red_png))
    captured = []
    presenter.report_html_ready.connect(captured.append)
    presenter.generate_report()
    assert captured, "no html emitted"
    assert 'class="report-image"' in captured[-1]


def test_exported_pdf_contains_attached_image_bytes(
    presenter, tmp_path, red_png,
):
    """The smoking-gun: with image attached, the PDF must be larger."""
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
        pytest.skip("requires offscreen Qt")
    _seeded_presenter(presenter)
    base = _baseline_pdf(presenter, tmp_path)
    base_size = base.stat().st_size

    presenter2 = presenter
    with_img = _with_image_pdf(presenter2, tmp_path, red_png)
    img_size = with_img.stat().st_size

    assert img_size > base_size, (
        f"PDF with image ({img_size} B) is not larger than baseline "
        f"({base_size} B) — image likely was not embedded"
    )


def test_clearing_attached_image_drops_it_from_next_export(
    presenter, tmp_path, red_png,
):
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
        pytest.skip("requires offscreen Qt")
    _seeded_presenter(presenter)
    presenter.set_attached_image(str(red_png))
    with_img = tmp_path / "with.pdf"
    presenter.export_pdf(str(with_img))
    s1 = with_img.stat().st_size

    presenter.set_attached_image(None)
    without = tmp_path / "without.pdf"
    presenter.export_pdf(str(without))
    s2 = without.stat().st_size
    assert s1 > s2, (
        f"after clearing image, PDF didn't shrink ({s1} → {s2})"
    )

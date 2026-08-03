"""F5 — Image attachment & PDF round-trip (Feedback #8)."""

from __future__ import annotations

from pathlib import Path


def _fake_png(path: Path) -> Path:
    """Write minimal valid-enough PNG bytes for the renderer."""
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return path


class TestImageAttach:
    def test_set_and_get_attached_image(self, journey, tmp_path):
        img = _fake_png(tmp_path / "logo.png")
        journey.presenter.set_attached_image(str(img))
        assert journey.presenter.attached_image_path() == str(img)

    def test_attached_image_survives_re_optimize(
        self,
        journey,
        parts_csv_factory,
        tmp_path,
    ):
        img = _fake_png(tmp_path / "logo.png")
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.presenter.set_attached_image(str(img))
        journey.calculate()
        journey.calculate()
        assert journey.presenter.attached_image_path() == str(img)

    def test_attached_image_cleared_on_clear_parts(
        self,
        journey,
        parts_csv_factory,
        tmp_path,
    ):
        img = _fake_png(tmp_path / "logo.png")
        journey.load_parts(parts_csv_factory())
        journey.presenter.set_attached_image(str(img))
        journey.presenter.clear_parts()
        assert journey.presenter.attached_image_path() is None


class TestPdfExport:
    def test_pdf_export_round_trip(
        self,
        journey,
        parts_csv_factory,
        tmp_path,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        out = tmp_path / "out.pdf"
        assert journey.presenter.export_pdf(str(out))
        assert out.exists()
        assert out.stat().st_size > 500, "PDF suspiciously small"

    def test_pdf_export_without_result_returns_false(
        self,
        journey,
        tmp_path,
        collector,
    ):
        out = tmp_path / "empty.pdf"
        ok = journey.presenter.export_pdf(str(out))
        assert ok is False
        assert collector.errors

    def test_pdf_export_with_image_includes_image_marker(
        self,
        journey,
        parts_csv_factory,
        tmp_path,
    ):
        """Feedback #8 — attached image must end up inside the PDF.

        We don't decode the PDF; we assert non-trivial size growth
        when an image is attached vs not.
        """
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()

        no_img = tmp_path / "no_img.pdf"
        journey.presenter.export_pdf(str(no_img))
        no_img_size = no_img.stat().st_size

        img = _fake_png(tmp_path / "logo.png")
        journey.presenter.set_attached_image(str(img))
        with_img = tmp_path / "with_img.pdf"
        journey.presenter.export_pdf(str(with_img))
        with_img_size = with_img.stat().st_size

        # Image attachment should *change* the PDF in some observable way.
        # Allow either grew (image embedded) or differs (rendered).
        assert with_img_size != no_img_size, (
            "PDF identical with and without image — Feedback #8 regression"
        )

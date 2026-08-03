"""F11 — Windows compatibility & responsive resizing."""

from __future__ import annotations

import sys


class TestWindowsCompat:
    def test_csv_exports_with_utf8_sig_bom(
        self,
        journey,
        parts_csv_factory,
        tmp_path,
    ):
        """Excel-on-Windows needs the UTF-8 BOM."""
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        out = tmp_path / "out.csv"
        journey.presenter.export_csv(str(out))
        assert out.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_no_console_kwargs_windows_only(self):
        """The Tekla provider must suppress the console window on Windows."""
        from tekla_nest.providers.tekla_provider import _no_console_kwargs

        kw = _no_console_kwargs()
        if sys.platform == "win32":
            import subprocess as sp

            assert kw.get("creationflags", 0) & getattr(sp, "CREATE_NO_WINDOW", 0x08000000)
        else:
            assert kw == {}

    def test_paths_with_unicode_load(self, journey, tmp_path, collector):
        """Windows paths with non-ASCII characters must load."""
        d = tmp_path / "Müller_é_中"
        d.mkdir()
        csv = d / "parts.csv"
        csv.write_text(
            "Quantidade;comprimento;referencia;perfil;material\n2;3000;A1;HEA240;S275JR\n",
            encoding="utf-8",
        )
        journey.presenter.load_parts_from_csv(str(csv))
        assert not collector.errors, f"Unicode path triggered error: {collector.errors}"
        assert len(journey.presenter._parts) >= 1


class TestResponsiveResize:
    def test_window_resize_does_not_crash(self, journey):
        from PySide6.QtWidgets import QApplication

        for w, h in [(800, 600), (1200, 800), (1920, 1080), (640, 480)]:
            journey.window.resize(w, h)
            journey.window.updateGeometry()
            QApplication.processEvents()
            # Window enforces its own min size — what matters is no crash
            # and width/height are positive.
            size = journey.window.size()
            assert size.width() > 0 and size.height() > 0

    def test_widgets_remain_visible_after_extreme_resize(self, journey):
        """Shrink to a tiny size — widgets must still exist & remain reachable."""
        journey.window.resize(400, 300)
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
        # All the key widgets must still be present
        assert journey.window._parts_table is not None
        assert journey.window._stock_tabs is not None
        assert journey.window._report_preview is not None

    def test_small_then_large_resize_keeps_purchase_table(
        self,
        journey,
        parts_csv_factory,
    ):
        from PySide6.QtWidgets import QApplication

        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        rows_before = journey.purchase_row_count()
        journey.window.resize(500, 400)
        QApplication.processEvents()
        journey.window.resize(1600, 1000)
        QApplication.processEvents()
        assert journey.purchase_row_count() == rows_before

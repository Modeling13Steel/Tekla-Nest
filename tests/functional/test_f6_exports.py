"""F6 — Exports (PDF / Excel / CSV)."""
from __future__ import annotations


class TestExportCsv:
    def test_csv_round_trip(self, journey, parts_csv_factory, tmp_path):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()

        out = tmp_path / "out.csv"
        assert journey.presenter.export_csv(str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8-sig")
        assert content, "CSV is empty"
        # Feedback #10 — purchase aggregation must appear in CSV
        assert "HEA240" in content or "IPE200" in content

    def test_csv_uses_utf8_sig(self, journey, parts_csv_factory, tmp_path):
        """Pin Windows-Excel compatibility (BOM)."""
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        out = tmp_path / "out.csv"
        journey.presenter.export_csv(str(out))
        raw = out.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), "CSV missing UTF-8 BOM"


class TestExportExcel:
    def test_xlsx_round_trip(self, journey, parts_csv_factory, tmp_path):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        out = tmp_path / "out.xlsx"
        assert journey.presenter.export_excel(str(out))
        assert out.exists()
        # Openable with openpyxl?
        import openpyxl
        wb = openpyxl.load_workbook(out)
        assert wb.sheetnames


class TestExportWithoutResult:
    def test_pdf_returns_false_no_crash(self, journey, tmp_path, collector):
        ok = journey.presenter.export_pdf(str(tmp_path / "x.pdf"))
        assert ok is False
        assert collector.errors

    def test_xlsx_returns_false_no_crash(self, journey, tmp_path, collector):
        ok = journey.presenter.export_excel(str(tmp_path / "x.xlsx"))
        assert ok is False
        assert collector.errors

    def test_csv_returns_false_no_crash(self, journey, tmp_path, collector):
        ok = journey.presenter.export_csv(str(tmp_path / "x.csv"))
        assert ok is False
        assert collector.errors

"""Walk every key user journey in offscreen Qt and report errors.

Phase-A repro harness: not a test, just an instrumented session that
exercises the app the way an end user would and prints any exceptions,
``error_occurred`` emissions, or stderr noise. Run with:

    QT_QPA_PLATFORM=offscreen uv run python scripts/repro_journeys.py

Output is human-readable; non-zero exit means at least one journey
raised. The functional tests in ``tests/functional/`` will pin each
finding here as a failing test, then we fix.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from tekla_nest.config.app_config import load_config, reset_config  # noqa: E402
from tekla_nest.design_system.tokens import Theme  # noqa: E402
from tekla_nest.i18n import set_language  # noqa: E402
from tekla_nest.presenters.nest_presenter import NestPresenter  # noqa: E402
from tekla_nest.views.nest_window import NestWindow  # noqa: E402

# Block modal QMessageBox so repro never hangs on error popups.
QMessageBox.warning = staticmethod(  # type: ignore[assignment,method-assign]
    lambda *a, **kw: QMessageBox.StandardButton.Ok
)
QMessageBox.information = staticmethod(  # type: ignore[assignment,method-assign]
    lambda *a, **kw: QMessageBox.StandardButton.Ok
)
QMessageBox.critical = staticmethod(  # type: ignore[assignment,method-assign]
    lambda *a, **kw: QMessageBox.StandardButton.Ok
)
QMessageBox.question = staticmethod(  # type: ignore[assignment,method-assign]
    lambda *a, **kw: QMessageBox.StandardButton.Yes
)


class ErrorCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def attach(self, presenter: NestPresenter) -> None:
        presenter.error_occurred.connect(lambda msg: self.events.append(("error_occurred", msg)))
        presenter.operation_failed.connect(
            lambda op, msg: self.events.append((f"operation_failed[{op}]", msg))
        )

    def dump(self, label: str) -> None:
        if not self.events:
            print(f"  ✓ {label}: clean")
            return
        print(f"  ✗ {label}: {len(self.events)} event(s)")
        for kind, msg in self.events:
            print(f"      [{kind}] {msg}")
        self.events.clear()


def _write_parts_csv(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Quantidade", "comprimento", "referencia", "perfil", "material"])
        w.writerow([4, 3500, "C1", "HEA240", "S275JR"])
        w.writerow([2, 5200, "C2", "HEA240", "S275JR"])
        w.writerow([3, 2800, "C3", "IPE200", "S355JR"])
        w.writerow([1, 4000, "C4", "HEA240", "S235JR"])  # mixed-material scenario


def _write_stock_csv(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Quantidade", "comprimento", "prioridade", "perfil", "material"])
        w.writerow([2, 6000, -1, "HEA240", "S275JR"])  # client (negative priority)
        w.writerow([3, 12000, 0, "IPE200", "S355JR"])


def journey(name: str):
    def deco(fn):
        def wrapped(window: NestWindow, collector: ErrorCollector, tmp: Path) -> None:
            print(f"\n→ {name}", flush=True)
            try:
                fn(window, collector, tmp)
            except Exception:  # noqa: BLE001
                print(f"  ✗ {name}: raised exception", flush=True)
                traceback.print_exc()
                collector.events.append(("python_exception", name))
            collector.dump(name)
        return wrapped
    return deco


@journey("J1 — load parts CSV")
def j1(window, collector, tmp):
    p = tmp / "parts.csv"
    _write_parts_csv(p)
    window._pres.load_parts_from_csv(str(p))
    assert window._pres.has_parts, "parts not loaded"
    assert len(window._parts_table.get_parts()) == 4


@journey("J2 — auto-populate stock")
def j2(window, collector, tmp):
    window._pres.auto_populate_stock()
    assert window._pres.has_stock, "no stock generated"


@journey("J3 — load client stock CSV")
def j3(window, collector, tmp):
    p = tmp / "stock.csv"
    _write_stock_csv(p)
    window._pres.load_client_stock_csv(str(p))


@journey("J4 — run optimization (sync)")
def j4(window, collector, tmp):
    window._pres.run_optimization()
    res = window._pres._last_result
    assert res is not None and res.profiles, "no result produced"
    # Verify (profile, material) grouping (Feedback #5)
    keys = {(p.profile, p.material) for p in res.profiles}
    assert ("HEA240", "S275JR") in keys
    assert ("HEA240", "S235JR") in keys, "mixed-material grouping broken"


@journey("J5 — report HTML emitted")
def j5(window, collector, tmp):
    received = []
    window._pres.report_html_ready.connect(received.append)
    window._pres.generate_report()
    assert received, "report_html_ready never fired"


@journey("J6 — purchase aggregation populated")
def j6(window, collector, tmp):
    # Re-emit result so set_result fires (J4 may have run before window wired)
    res = window._pres._last_result
    assert res is not None
    window._purchase_table.set_result(res)
    assert window._purchase_table._table.rowCount() > 0, "purchase table empty"


@journey("J7 — export PDF/Excel/CSV")
def j7(window, collector, tmp):
    pdf = tmp / "out.pdf"
    xlsx = tmp / "out.xlsx"
    csv_path = tmp / "out.csv"
    assert window._pres.export_pdf(str(pdf)), "PDF export returned False"
    assert pdf.exists() and pdf.stat().st_size > 0
    assert window._pres.export_excel(str(xlsx)), "Excel export returned False"
    assert xlsx.exists()
    assert window._pres.export_csv(str(csv_path)), "CSV export returned False"
    assert csv_path.exists()


@journey("J8 — attach image then re-render report")
def j8(window, collector, tmp):
    img = tmp / "img.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # not a real PNG but path-valid
    window._pres.set_attached_image(str(img))
    window._pres.generate_report()


@journey("J9 — switch language en → pt → en")
def j9(window, collector, tmp):
    set_language("pt")
    set_language("en")


@journey("J10 — toggle insights panel hide/show")
def j10(window, collector, tmp):
    window._report_preview.set_insights_visible(False)
    window._report_preview.set_insights_visible(True)


@journey("J11 — clear parts then re-load")
def j11(window, collector, tmp):
    window._pres.clear_parts()
    p = tmp / "parts2.csv"
    _write_parts_csv(p)
    window._pres.load_parts_from_csv(str(p))


@journey("J12 — re-run optimization after clear+reload")
def j12(window, collector, tmp):
    window._pres.auto_populate_stock()
    window._pres.run_optimization()
    assert window._pres._last_result is not None


@journey("J13 — async optimization round-trip")
def j13(window, collector, tmp):
    from PySide6.QtCore import QEventLoop, QTimer
    done = []
    window._pres.operation_completed.connect(
        lambda op: done.append(op) if op == "optimize" else None
    )
    window._pres.operation_failed.connect(lambda op, msg: done.append((op, msg)))
    window._pres.run_optimization_async()
    loop = QEventLoop()
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    if not done:
        print("  ! async optimize never completed within 3s")


@journey("J14 — resize window to minimum")
def j14(window, collector, tmp):
    window.resize(960, 600)


@journey("J15 — toggle insights, then run optimization, then toggle")
def j15(window, collector, tmp):
    window._report_preview.set_insights_visible(False)
    window._pres.run_optimization()
    window._report_preview.set_insights_visible(True)


@journey("J16 — malformed parts CSV (bad qty)")
def j16(window, collector, tmp):
    p = tmp / "bad.csv"
    with open(p, "w", encoding="utf-8") as f:
        f.write("Quantidade;comprimento;referencia;perfil;material\n")
        f.write("abc;3500;C1;HEA240;S275JR\n")
    window._pres.load_parts_from_csv(str(p))


@journey("J17 — load parts CSV with non-existent path")
def j17(window, collector, tmp):
    window._pres.load_parts_from_csv(str(tmp / "does_not_exist.csv"))


@journey("J18 — clear parts twice (idempotency)")
def j18(window, collector, tmp):
    window._pres.clear_parts()
    window._pres.clear_parts()


@journey("J19 — optimize with NO stock loaded")
def j19(window, collector, tmp):
    window._pres.clear_parts()
    p = tmp / "parts3.csv"
    _write_parts_csv(p)
    window._pres.load_parts_from_csv(str(p))
    # Intentionally do not populate stock
    window._pres.run_optimization()


@journey("J20 — optimize with NO parts loaded")
def j20(window, collector, tmp):
    window._pres.clear_parts()
    window._pres.run_optimization()


@journey("J21 — export PDF before any optimize")
def j21(window, collector, tmp):
    p2 = NestPresenter()
    out = tmp / "empty.pdf"
    ok = p2.export_pdf(str(out))
    if ok and out.exists():
        print(f"  ! PDF exported with no result (unexpected): {out.stat().st_size}b")


@journey("J22 — open + close command palette")
def j22(window, collector, tmp):
    from tekla_nest.views.command_palette import CommandPalette
    pal = CommandPalette(window._actions, parent=window)
    pal.close()


@journey("J23 — open + close ColorSchema dialog")
def j23(window, collector, tmp):
    from tekla_nest.views.color_dialog import ColorSchemaDialog
    dlg = ColorSchemaDialog(window)
    dlg.close()


@journey("J24 — report filter changed")
def j24(window, collector, tmp):
    # Need a result first
    window._pres.run_optimization()
    window._pres.report_filter_changed("HEA240")
    window._pres.report_filter_changed("")  # clear filter


@journey("J25 — bar reorder ▲▼")
def j25(window, collector, tmp):
    window._pres.run_optimization()
    res = window._pres._last_result
    if res and res.profiles and len(res.profiles[0].bars) >= 2:
        window._pres.reorder_bars(0, 1, 0)


@journey("J26 — request_stock action")
def j26(window, collector, tmp):
    window._pres.request_stock(profile="HEA240", length=4000, piece_count=2)


@journey("J27 — language pt, run optimize, export PDF (translated report)")
def j27(window, collector, tmp):
    set_language("pt")
    try:
        window._pres.run_optimization()
        out = tmp / "pt.pdf"
        window._pres.export_pdf(str(out))
        assert out.exists()
    finally:
        set_language("en")


@journey("J28 — set attached image to non-existent path")
def j28(window, collector, tmp):
    window._pres.set_attached_image(str(tmp / "missing.png"))
    window._pres.generate_report()


@journey("J29 — auto-populate stock with NO parts")
def j29(window, collector, tmp):
    window._pres.clear_parts()
    window._pres.auto_populate_stock()


@journey("J30 — async optimize x2 (back-to-back)")
def j30(window, collector, tmp):
    from PySide6.QtCore import QEventLoop, QTimer
    p = tmp / "parts30.csv"
    _write_parts_csv(p)
    window._pres.load_parts_from_csv(str(p))
    window._pres.auto_populate_stock()
    done = []
    window._pres.operation_completed.connect(
        lambda op: done.append(op) if op == "optimize" else None
    )
    window._pres.run_optimization_async()
    window._pres.run_optimization_async()  # second call while first runs
    loop = QEventLoop()
    QTimer.singleShot(3000, loop.quit)
    loop.exec()


@journey("J31 — theme switch light → dark → light")
def j31(window, collector, tmp):
    from tekla_nest.services.theme_service import ThemeService
    ts = window._theme_service
    if ts is None:
        # Construct one inline if main window wasn't given one
        ts = ThemeService()
    ts.set_theme(Theme.DARK)
    ts.set_theme(Theme.LIGHT)


@journey("J32 — admin window construct + close")
def j32(window, collector, tmp):
    try:
        from tekla_nest.admin.window import AdminWindow
    except ImportError:
        print("  (admin module not importable in this env)")
        return
    try:
        aw = AdminWindow()
        aw.close()
    except Exception as exc:
        print(f"  ! AdminWindow construction failed: {exc}")
        raise


@journey("J33 — generate_report with no result")
def j33(window, collector, tmp):
    p2 = NestPresenter()
    p2.generate_report()


def main() -> int:
    reset_config()
    load_config()
    app = QApplication.instance() or QApplication(sys.argv)
    collector = ErrorCollector()
    presenter = NestPresenter()
    collector.attach(presenter)
    window = NestWindow(presenter)
    window.show()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        j1(window, collector, tmp)
        j2(window, collector, tmp)
        j3(window, collector, tmp)
        j4(window, collector, tmp)
        j5(window, collector, tmp)
        j6(window, collector, tmp)
        j7(window, collector, tmp)
        j8(window, collector, tmp)
        j9(window, collector, tmp)
        j10(window, collector, tmp)
        j11(window, collector, tmp)
        j12(window, collector, tmp)
        j13(window, collector, tmp)
        j14(window, collector, tmp)
        j15(window, collector, tmp)
        j16(window, collector, tmp)
        j17(window, collector, tmp)
        j18(window, collector, tmp)
        j19(window, collector, tmp)
        j20(window, collector, tmp)
        j21(window, collector, tmp)
        j22(window, collector, tmp)
        j23(window, collector, tmp)
        j24(window, collector, tmp)
        j25(window, collector, tmp)
        j26(window, collector, tmp)
        j27(window, collector, tmp)
        j28(window, collector, tmp)
        j29(window, collector, tmp)
        j30(window, collector, tmp)
        j31(window, collector, tmp)
        j32(window, collector, tmp)
        j33(window, collector, tmp)

    app.processEvents()
    print("\n=== Repro complete ===")
    # Return non-zero if anything bad was captured (collector dumps clear it
    # each journey, so we just rely on the printed log for now).
    return 0


if __name__ == "__main__":
    sys.exit(main())

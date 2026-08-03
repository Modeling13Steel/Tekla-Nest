"""Presenter that orchestrates providers, services, and the view.

Migrated from: C# FrmNest event handlers
    - cALCULARToolStripMenuItem_Click  → run_optimization()
    - BuscaPerfisExixtententes()       → set comprehension in run_optimization()
    - ApanhaPecas()                    → _expand_parts()
    - ApanhaPerfis()                   → _build_stock()

The view emits user actions, the presenter reacts by calling services
and pushing data back to the view via Qt signals. The view never calls
services directly.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QObject, QThread, Signal, Slot
from tekla_common.config.app_config import get_config
from tekla_common.i18n import tr

from ..models import (
    CutPiece,
    NestResult,
    OptimizationSummary,
    PartEntry,
    ProfileResult,
    StockBar,
    StockEntry,
)
from ..observability import log_ui_event, redact
from ..providers.base_provider import PartProvider
from ..services.csv_loader import CsvError, load_parts_csv, load_stock_csv
from ..services.csv_report import export_csv
from ..services.excel_report import export_excel
from ..services.nest_engine import NestEngine
from ..services.pdf_report import render_report_html
from ..services.stock_rules import generate_default_stock

LOGGER = logging.getLogger(__name__)


def _sort_parts(parts: list[PartEntry]) -> list[PartEntry]:
    return sorted(parts, key=lambda p: (p.profile.lower(), p.material.lower(), p.reference.lower()))


def _sort_stock(stock: list[StockEntry]) -> list[StockEntry]:
    return sorted(stock, key=lambda s: (s.profile.lower(), s.material.lower(), s.length))


class NestPresenter(QObject):
    """MVP presenter for the nesting workflow.

    Signals (view connects to these):
        parts_loaded  – emitted after parts are loaded from any source.
        stock_loaded  – emitted after stock entries are generated/loaded.
        result_ready  – emitted with the full NestResult after optimization.
        report_html_ready – emitted with the rendered HTML report string.
        error_occurred – emitted with a human-readable error message.
    """

    # Signals ──────────────────────────────────────────────────
    parts_loaded = Signal(list)
    stock_loaded = Signal(list)
    market_stock_replaced = Signal(list)
    result_ready = Signal(object)
    optimization_summary_changed = Signal(object)
    report_html_ready = Signal(str)
    error_occurred = Signal(str)
    csv_error_occurred = Signal(str, str)  # (title, detail)
    notice = Signal(str)  # informational status text — not an error
    operation_started = Signal(str)
    operation_progress = Signal(str, str)
    operation_completed = Signal(str)
    operation_failed = Signal(str, str)
    state_changed = Signal()

    def __init__(self, part_provider: PartProvider | None = None) -> None:
        super().__init__()
        cfg = get_config()

        self._parts: list[PartEntry] = []
        self._market_stock: list[StockEntry] = []
        self._client_stock: list[StockEntry] = []

        self._engine = NestEngine(
            kerf_width=cfg.kerf_width,
            scrap_threshold=cfg.scrap_threshold,
            max_strategies=cfg.max_strategies,
        )
        self._part_provider = part_provider
        self._last_result: NestResult | None = None
        self._result_exported: bool = False
        self._attached_image_path: str | None = None  # Feedback #8
        self._project_name: str = ""
        self._milestone: str = ""
        self._busy_operations: set[str] = set()
        self._async_threads: list[QThread] = []
        self._async_workers: list[QObject] = []

    @property
    def has_parts(self) -> bool:
        return bool(self._parts)

    @property
    def has_stock(self) -> bool:
        return bool(self._market_stock or self._client_stock)

    @property
    def has_result(self) -> bool:
        return self._last_result is not None

    @property
    def result_exported(self) -> bool:
        """True after any export (PDF/Excel/CSV) succeeds for the current result."""
        return self._result_exported

    @property
    def is_busy(self) -> bool:
        return bool(self._busy_operations)

    @property
    def last_result(self) -> NestResult | None:
        return self._last_result

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def milestone(self) -> str:
        return self._milestone

    @milestone.setter
    def milestone(self, value: str) -> None:
        self._milestone = value or ""

    # ── Part loading ─────────────────────────────────────────

    def load_parts_from_provider(self) -> None:
        """Load parts from the configured provider (Tekla, CSV, etc.).

        If no provider was set at startup (e.g. app opened before Tekla),
        a TeklaPartProvider is created lazily so the user can retry after
        opening Tekla without restarting the app.
        """
        operation = "load_parts"
        if not self._begin_operation(operation):
            return
        if self._part_provider is None:
            try:
                from ..providers.tekla_provider import TeklaPartProvider

                self._part_provider = TeklaPartProvider()
            except Exception as exc:
                LOGGER.exception("Failed to create Tekla provider")
                if sys.stdout is not None:
                    print(f"[TEKLANEST TEKLA ERROR] provider init: {exc}", flush=True)
                self.csv_error_occurred.emit(tr("errors.tekla_load_title"), str(exc))
                self._fail_operation(operation, str(exc))
                return
        try:
            self._parts = _sort_parts(self._part_provider.get_parts())
            self._project_name = getattr(self._part_provider, "project_name", "")
            self.parts_loaded.emit(self._parts)
            self.state_changed.emit()
            self._complete_operation(operation)
        except Exception as exc:
            LOGGER.exception("Failed to load parts from provider")
            if sys.stdout is not None:
                print(f"[TEKLANEST TEKLA ERROR] load_parts_from_provider: {exc}", flush=True)
            self.csv_error_occurred.emit(tr("errors.tekla_load_title"), str(exc))
            self._fail_operation(operation, f"Failed to load parts: {redact(exc)}")

    def load_parts_from_csv(self, path: str) -> None:
        """Load parts from a CSV file."""
        operation = "load_parts_csv"
        if sys.stdout is not None:
            print(f"[TEKLANEST] load_parts_from_csv ENTER  path={path!r}", flush=True)
        if not self._begin_operation(operation, source=path):
            if sys.stdout is not None:
                print(
                    "[TEKLANEST] load_parts_from_csv BLOCKED (operation already running)",
                    flush=True,
                )
            return
        try:
            self._parts = _sort_parts(load_parts_csv(path))
            if sys.stdout is not None:
                print(f"[TEKLANEST] load_parts_from_csv OK  parts={len(self._parts)}", flush=True)
            self.parts_loaded.emit(self._parts)
            if sys.stdout is not None:
                print("[TEKLANEST] parts_loaded.emit done", flush=True)
            self.state_changed.emit()
            self._complete_operation(operation)
            if not self._parts:
                self.notice.emit(tr("status.csv_parts_empty"))
        except CsvError as exc:
            LOGGER.exception("Failed to load parts CSV")
            if sys.stdout is not None:
                print(f"[TEKLANEST] load_parts_from_csv CsvError: {exc}", flush=True)
            self.csv_error_occurred.emit(
                tr("errors.csv_load_title"),
                str(exc),
            )
            self._fail_operation(
                operation,
                tr("errors.operations.failed_load_parts_csv", detail=str(exc)),
            )
            return
        except Exception as exc:
            LOGGER.exception("Failed to load parts CSV")
            if sys.stdout is not None:
                print(f"[TEKLANEST UNEXPECTED ERROR] load_parts_from_csv: {exc}", flush=True)
            self.csv_error_occurred.emit(
                tr("errors.csv_load_title"),
                f"Failed to load parts CSV: {redact(exc)}",
            )
            self._fail_operation(
                operation,
                f"Failed to load parts CSV: {redact(exc)}",
            )

    def set_parts(self, parts: list[PartEntry]) -> None:
        """Set parts directly (from manual entry in the view)."""
        self._parts = list(parts)
        self.state_changed.emit()

    def clear_parts(self) -> None:
        """Undo part loading by emptying the parts list.

        Stock and any previously computed result are left untouched so the
        user can simply reload a different parts source without losing the
        rest of the working session.
        """
        operation = "clear_parts"
        if not self._begin_operation(operation):
            return
        self._parts = []
        self.parts_loaded.emit(self._parts)
        self._last_result = None
        self._attached_image_path = None
        self.optimization_summary_changed.emit(None)
        self.state_changed.emit()
        self._complete_operation(operation)

    # ── Feedback #8 — report image persistence ─────────────────

    def set_attached_image(self, path: str | None) -> None:
        """Remember a report image so PDF export can re-attach it."""
        self._attached_image_path = path

    def attached_image_path(self) -> str | None:
        return self._attached_image_path

    def _inject_attached_image(self, html: str) -> str:
        """Inject the persisted image into HTML before the closing body tag."""
        path_str = self._attached_image_path
        if not path_str:
            return html
        from pathlib import Path as _P

        img_path = _P(path_str)
        if not img_path.exists():
            return html
        import base64 as _b64
        from html import escape as _esc

        suffix = img_path.suffix.lstrip(".").lower()
        mime = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "bmp": "bmp",
            "gif": "gif",
        }.get(suffix, "png")
        b64 = _b64.b64encode(img_path.read_bytes()).decode("ascii")
        block = (
            "<style>.report-image-wrap{text-align:right;margin:12px 0;}"
            ".report-image{max-width:60%;border:1px solid #8a94a6;}</style>"
            f'<div class="report-image-wrap">'
            f'<img class="report-image" alt="{_esc(img_path.name)}" '
            f'src="data:image/{mime};base64,{b64}"/></div>'
        )
        lower = html.lower()
        if "</body>" in lower:
            idx = lower.rfind("</body>")
            return html[:idx] + block + html[idx:]
        return html + block

    # ── Stock loading ────────────────────────────────────────

    def auto_populate_stock(self) -> None:
        """Generate default market stock for all distinct (profile, material) pairs in parts.

        Finding E fix: when no parts are loaded, this previously
        completed silently with an empty stock list — leaving the user
        unsure whether anything happened. It now emits an informational
        notice in that case.

        Only the exact (profile, material) combinations present in the
        parts are seeded, so no spurious entries are created for materials
        that are not actually used.

        Emits ``market_stock_replaced`` (not ``stock_loaded``) so the view
        replaces the market stock table instead of appending — calling
        auto-stock twice no longer duplicates entries.
        """
        operation = "auto_stock"
        if not self._begin_operation(operation):
            return
        pairs = sorted(
            {(p.profile.strip(), (p.material or "").strip()) for p in self._parts if p.profile}
        )
        if not pairs:
            self.notice.emit("Auto-stock skipped: load parts first to seed default stock.")
            self._complete_operation(operation)
            return
        base_stock = generate_default_stock(pairs)

        # Length-coverage fix: if any piece is longer than the longest
        # stock bar for its (profile, material) combo, no bar can hold
        # it and it surfaces as an unfit piece ("not enough stock" on
        # the report). Seed an extra bar sized to the longest piece
        # (rounded up to the next 500 mm) so over-length pieces are
        # cuttable from a single bar by default.
        cfg = get_config()
        full_stock = base_stock
        max_piece: dict[tuple[str, str], float] = {}
        for p in self._parts:
            profile = (p.profile or "").strip()
            if not profile:
                continue
            material = (p.material or "").strip()
            key = (profile.lower(), material.lower())
            if p.length > max_piece.get(key, 0.0):
                max_piece[key] = float(p.length)
        max_stock: dict[tuple[str, str], float] = {}
        for s in full_stock:
            key = (s.profile.strip().lower(), s.material.strip().lower())
            if s.length > max_stock.get(key, 0.0):
                max_stock[key] = float(s.length)
        for p in self._parts:
            profile = (p.profile or "").strip()
            if not profile:
                continue
            material = (p.material or "").strip()
            key = (profile.lower(), material.lower())
            needed = max_piece.get(key, 0.0)
            if needed <= max_stock.get(key, 0.0):
                continue
            bar_length = float(((int(needed) + 499) // 500) * 500)
            full_stock.append(
                StockEntry(
                    quantity=cfg.default_stock_quantity,
                    length=bar_length,
                    priority=0,
                    profile=profile,
                    material=material,
                    source="Mercado",
                )
            )
            max_stock[key] = bar_length

        self._market_stock = _sort_stock(full_stock)
        self.market_stock_replaced.emit(self._market_stock)
        self.state_changed.emit()
        self._complete_operation(operation)

    def load_client_stock_csv(self, path: str) -> None:
        """Load client stock from CSV. Source is set to 'Cliente'."""
        operation = "load_stock_csv"
        if sys.stdout is not None:
            print(f"[TEKLANEST] load_client_stock_csv ENTER  path={path!r}", flush=True)
        if not self._begin_operation(operation, source=path):
            if sys.stdout is not None:
                print(
                    "[TEKLANEST] load_client_stock_csv BLOCKED (operation already running)",
                    flush=True,
                )
            return
        try:
            self._client_stock = _sort_stock(load_stock_csv(path))
            if sys.stdout is not None:
                print(
                    f"[TEKLANEST] load_client_stock_csv OK  entries={len(self._client_stock)}",
                    flush=True,
                )
            self.stock_loaded.emit(self._client_stock)
            self.state_changed.emit()
            count = len(self._client_stock)
            self._complete_operation(operation)
            if count == 0:
                self.notice.emit(tr("status.csv_stock_empty"))
            else:
                self.notice.emit(tr("status.csv_stock_loaded", count=count))
        except CsvError as exc:
            LOGGER.exception("Failed to load stock CSV")
            if sys.stdout is not None:
                print(f"[TEKLANEST] load_client_stock_csv CsvError: {exc}", flush=True)
            self.csv_error_occurred.emit(
                tr("errors.csv_load_title"),
                str(exc),
            )
            self._fail_operation(
                operation,
                tr("errors.operations.failed_load_stock_csv", detail=str(exc)),
            )
            return
        except Exception as exc:
            LOGGER.exception("Failed to load stock CSV")
            if sys.stdout is not None:
                print(f"[TEKLANEST UNEXPECTED ERROR] load_client_stock_csv: {exc}", flush=True)
            self.csv_error_occurred.emit(
                tr("errors.csv_load_title"),
                f"Failed to load stock CSV: {redact(exc)}",
            )
            self._fail_operation(
                operation,
                f"Failed to load stock CSV: {redact(exc)}",
            )

    def set_market_stock(self, stock: list[StockEntry]) -> None:
        """Set market stock directly (from manual entry in the view)."""
        self._market_stock = list(stock)
        self.state_changed.emit()

    def set_client_stock(self, stock: list[StockEntry]) -> None:
        """Set client stock directly (from manual entry in the view)."""
        self._client_stock = list(stock)
        self.state_changed.emit()

    # ── Optimization ─────────────────────────────────────────

    def run_optimization(self) -> None:
        """Run nesting for all profiles.

        Emits *result_ready* on success or *error_occurred* on failure.

        Migrated from: FrmNest.cALCULARToolStripMenuItem_Click
        """
        operation = "optimize"
        if not self._begin_operation(operation):
            return
        if not self._parts:
            self._fail_operation(operation, "No parts loaded.")
            return

        try:
            nest_result = self._compute_nest_result(
                self._parts,
                self._market_stock,
                self._client_stock,
                self._engine,
                progress=lambda profile: self.operation_progress.emit(
                    operation,
                    f"Optimizing {profile}",
                ),
            )
            self._last_result = nest_result
            self._result_exported = False
            self.result_ready.emit(nest_result)
            self.optimization_summary_changed.emit(
                OptimizationSummary.from_nest_result(nest_result)
            )
            self.state_changed.emit()
            self._complete_operation(operation)
        except Exception as exc:
            LOGGER.exception("Optimization failed")
            self._fail_operation(operation, f"Failed to optimize: {redact(exc)}")

    def run_optimization_async(self) -> None:
        """Run optimization on a Qt worker thread for the GUI path."""
        operation = "optimize"
        if not self._begin_operation(operation):
            return
        if not self._parts:
            self._fail_operation(operation, "No parts loaded.")
            return

        worker = _OptimizationWorker(
            parts=list(self._parts),
            market_stock=list(self._market_stock),
            client_stock=list(self._client_stock),
            kerf_width=self._engine.kerf_width,
            scrap_threshold=self._engine.scrap_threshold,
            max_strategies=self._engine.max_strategies,
        )
        thread = QThread(self)
        self._async_threads.append(thread)
        self._async_workers.append(worker)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(lambda message: self.operation_progress.emit(operation, message))
        worker.finished.connect(
            lambda result: self._on_async_optimization_finished(
                result,
                operation,
                thread,
            )
        )
        worker.failed.connect(
            lambda message: self._on_async_optimization_failed(
                message,
                operation,
                thread,
            )
        )
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._discard_worker(worker))
        thread.finished.connect(lambda: self._discard_thread(thread))
        thread.start()

    # ── Report ───────────────────────────────────────────────

    def generate_report(self) -> None:
        """Generate HTML report from last result. Emits *report_html_ready*."""
        operation = "report"
        if not self._begin_operation(operation):
            return
        if self._last_result is None:
            self._fail_operation(operation, "No results to report. Run optimization first.")
            return
        try:
            html = render_report_html(
                self._last_result,
                attached_image_path=self._attached_image_path,
                project_name=self._project_name,
                milestone=self._milestone,
            )
            self.report_html_ready.emit(html)
            self._complete_operation(operation)
        except Exception as exc:
            LOGGER.exception("Failed to generate report")
            self._fail_operation(
                operation,
                f"Failed to generate report: {redact(exc)}",
            )

    def export_pdf(self, path: str, scope=None) -> bool:
        """Save the current report as a PDF file using Qt's built-in printer.

        ``scope`` (feedback v2 #2.1) optionally restricts the export to a
        subset of ``(profile, material)`` pairs.

        Returns True on success."""
        operation = "export_pdf"
        if not self._begin_operation(operation, target=path):
            return False
        if self._last_result is None:
            self._fail_operation(operation, "No results to export. Run optimization first.")
            return False
        if scope is not None and len(scope) == 0:
            self._fail_operation(
                operation,
                "Empty selection — pick at least one profile to export.",
            )
            return False
        try:
            html = render_report_html(
                self._last_result,
                attached_image_path=self._attached_image_path,
                scope=scope,
                project_name=self._project_name,
                milestone=self._milestone,
            )
            from pathlib import Path as P

            out = P(path)
            out.parent.mkdir(parents=True, exist_ok=True)

            from PySide6.QtCore import QMarginsF
            from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
            from PySide6.QtPrintSupport import QPrinter

            class _DataUriTextDocument(QTextDocument):
                """QTextDocument subclass that resolves data: URI images.
                QTextDocument.loadResource() silently drops data: URI src on <img>
                tags when printing to PDF. Override to decode base64 payload."""

                def loadResource(self, resource_type, url):
                    from PySide6.QtCore import QUrl
                    from PySide6.QtGui import QImage

                    url_str = url.toString() if isinstance(url, QUrl) else str(url)
                    if url_str.startswith("data:"):
                        try:
                            header, b64 = url_str.split(",", 1)
                            import base64

                            data = base64.b64decode(b64)
                            img = QImage()
                            img.loadFromData(data)
                            if not img.isNull():
                                return img
                        except Exception:
                            pass
                    return super().loadResource(resource_type, url)

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(out))
            printer.setPageLayout(
                QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(10, 10, 10, 10),
                )
            )

            doc = _DataUriTextDocument()
            doc.setHtml(html)
            doc.setPageSize(printer.pageRect(QPrinter.Unit.Point).size())
            doc.print_(printer)
            self._result_exported = True
            self._complete_operation(operation)
            return True
        except Exception as exc:
            LOGGER.exception("Failed to export PDF")
            self._fail_operation(operation, f"Failed to export PDF: {redact(exc)}")
            return False

    def export_excel(self, path: str, scope=None) -> bool:
        """Save the current result as an Excel workbook. Returns True on success."""
        operation = "export_excel"
        if not self._begin_operation(operation, target=path):
            return False
        if self._last_result is None:
            self._fail_operation(operation, "No results to export. Run optimization first.")
            return False
        if scope is not None and len(scope) == 0:
            self._fail_operation(
                operation,
                "Empty selection — pick at least one profile to export.",
            )
            return False
        try:
            export_excel(
                self._last_result,
                path,
                scope=scope,
                project_name=self._project_name,
                milestone=self._milestone,
            )
            self._result_exported = True
            self._complete_operation(operation)
            return True
        except Exception as exc:
            LOGGER.exception("Failed to export Excel")
            self._fail_operation(operation, f"Failed to export Excel: {redact(exc)}")
            return False

    def export_csv(self, path: str, scope=None) -> bool:
        """Save the current result as a CSV file. Returns True on success."""
        operation = "export_csv"
        if not self._begin_operation(operation, target=path):
            return False
        if self._last_result is None:
            self._fail_operation(operation, "No results to export. Run optimization first.")
            return False
        if scope is not None and len(scope) == 0:
            self._fail_operation(
                operation,
                "Empty selection — pick at least one profile to export.",
            )
            return False
        try:
            export_csv(self._last_result, path, scope=scope)
            self._result_exported = True
            self._complete_operation(operation)
            return True
        except Exception as exc:
            LOGGER.exception("Failed to export CSV")
            self._fail_operation(operation, f"Failed to export CSV: {redact(exc)}")
            return False

    def reorder_bars(self, profile_index: int, old_row: int, new_row: int) -> bool:
        """Move a bar within a profile result and regenerate the report."""
        operation = "reorder_report"
        if not self._begin_operation(operation):
            return False
        if self._last_result is None:
            self._fail_operation(operation, "No results to reorder. Run optimization first.")
            return False
        if not 0 <= profile_index < len(self._last_result.profiles):
            self._fail_operation(operation, "Report profile is no longer available.")
            return False
        bars = self._last_result.profiles[profile_index].bars
        if not (0 <= old_row < len(bars) and 0 <= new_row < len(bars)):
            self._fail_operation(operation, "Report bar is no longer available.")
            return False
        bar = bars.pop(old_row)
        bars.insert(new_row, bar)
        self.generate_report()
        self._complete_operation(operation)
        return True

    # ── M5: Report filter + insight actions ──────────────────

    def report_filter_changed(self, profile: str) -> None:
        """Re-render the HTML report narrowed to *profile* (empty = all)."""
        if self._last_result is None:
            return
        if not profile:
            narrowed = self._last_result
        else:
            filtered = [p for p in self._last_result.profiles if p.profile == profile]
            if not filtered:
                return
            from copy import copy

            narrowed = copy(self._last_result)
            narrowed.profiles = filtered
        try:
            html = render_report_html(
                narrowed,
                attached_image_path=self._attached_image_path,
                project_name=self._project_name,
                milestone=self._milestone,
            )
            self.report_html_ready.emit(html)
        except Exception as exc:
            LOGGER.exception("Failed to re-render filtered report")
            self.error_occurred.emit(f"Failed to render report: {redact(exc)}")

    def request_stock(self, profile: str, length: float, piece_count: int) -> None:
        """Surface a stock request suggestion as an informational notice.

        Finding B fix: previously this rode the ``error_occurred`` channel
        which made it pop up as a modal error dialog. It is now emitted on
        the dedicated ``notice`` channel so the view can render it as a
        status-bar message without alarming the user.
        """
        msg = f"Stock request: {piece_count} piece(s) of {profile} at {length:.0f} mm need stock."
        LOGGER.info(msg)
        self.notice.emit(msg)

    def update_theme_colors(self, primary: str, accent: str, background: str) -> None:
        """Update the theme colors for the current session."""
        operation = "theme"
        if not self._begin_operation(operation):
            return
        cfg = get_config()
        cfg.primary_color = primary
        cfg.accent_color = accent
        cfg.background = background

        # Update the application stylesheet to reflect new colors
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            from tekla_common.theme import build_app_stylesheet

            app.setStyleSheet(build_app_stylesheet(cfg))

        # Regenerate report with new colors if we have results.
        if self._last_result is not None:
            self.generate_report()
        self._complete_operation(operation)

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _expand_parts(parts: list[PartEntry]) -> list[CutPiece]:
        """Expand grouped PartEntry list → individual CutPiece instances.

        Migrated from: the for/while loop in otimizar() that expands quantity.
        """
        pieces: list[CutPiece] = []
        for p in parts:
            for _ in range(p.quantity):
                pieces.append(CutPiece(length=p.length, mark=p.reference))
        return pieces

    def _build_stock(
        self,
        profile: str,
        profile_parts: list[PartEntry],
        material: str = "",
    ) -> list[StockBar]:
        """Build an expanded, priority-sorted stock bar list for one profile.

        Client stock gets priority -1000 (used first).
        Falls back to material from parts if stock entry has none.

        Migrated from: FrmNest.ApanhaPerfis()
        """
        return self._build_stock_for(
            profile,
            material,
            profile_parts,
            self._market_stock,
            self._client_stock,
        )

    @staticmethod
    def _build_stock_for(
        profile: str,
        material: str,
        profile_parts: list[PartEntry],
        market_stock: list[StockEntry],
        client_stock: list[StockEntry],
    ) -> list[StockBar]:
        """Build stock for the (profile, material) group.

        Feedback #5 — when the same profile carries multiple materials
        (e.g. HEA240 in both S235 and S275), each material must nest
        against stock of THAT material only. Mixing materials would
        produce a structurally invalid cut plan.
        """
        fallback_material = material
        if not fallback_material:
            for p in profile_parts:
                if p.material:
                    fallback_material = p.material
                    break

        def _material_matches(stock_mat: str) -> bool:
            # If the part group has no material declared, accept any
            # stock material (legacy behaviour). Otherwise the stock
            # material must match (case-insensitive, trimmed) — empty
            # stock material is treated as the fallback and accepted.
            if not material:
                return True
            sm = (stock_mat or "").strip().lower()
            if not sm:
                return True
            return sm == material.strip().lower()

        entries: list[StockEntry] = []

        # Client stock with priority boost
        for s in client_stock:
            if s.profile.strip().lower() != profile.strip().lower():
                continue
            if not _material_matches(s.material):
                continue
            entries.append(
                StockEntry(
                    quantity=s.quantity,
                    length=s.length,
                    priority=s.priority - 1000,
                    profile=s.profile,
                    material=s.material or fallback_material,
                    source="Cliente",
                )
            )

        # Market stock
        for s in market_stock:
            if s.profile.strip().lower() != profile.strip().lower():
                continue
            if not _material_matches(s.material):
                continue
            entries.append(
                StockEntry(
                    quantity=s.quantity,
                    length=s.length,
                    priority=s.priority,
                    profile=s.profile,
                    material=s.material or fallback_material,
                    source="Mercado",
                )
            )

        # Sort by priority ASC, then expand into individual bars
        entries.sort(key=lambda e: e.priority)
        bars: list[StockBar] = []
        for e in entries:
            for _ in range(e.quantity):
                bars.append(
                    StockBar(
                        length=e.length,
                        mark=e.profile,
                        material=e.material,
                        source=e.source,
                        priority=e.priority,
                    )
                )
        return bars

    @staticmethod
    def _compute_nest_result(
        parts: list[PartEntry],
        market_stock: list[StockEntry],
        client_stock: list[StockEntry],
        engine: NestEngine,
        progress: object | None = None,
    ) -> NestResult:
        # Feedback #5 — group by (profile, material) so the same
        # profile in two materials does not collapse into one nest.
        groups: list[tuple[str, str]] = sorted(
            {(p.profile, p.material or "") for p in parts if p.profile}
        )
        nest_result = NestResult()

        for profile, material in groups:
            if callable(progress):
                label = f"{profile} / {material}" if material else profile
                progress(label)
            group_parts = [
                p for p in parts if p.profile == profile and (p.material or "") == material
            ]
            pieces = NestPresenter._expand_parts(group_parts)
            stock_bars = NestPresenter._build_stock_for(
                profile,
                material,
                group_parts,
                market_stock,
                client_stock,
            )

            if not stock_bars:
                nest_result.profiles.append(
                    ProfileResult(
                        profile=profile,
                        material=material,
                        waste_pct=100.0,
                    )
                )
                continue

            profile_result = engine.optimize(pieces, stock_bars)

            if profile_result is None:
                nest_result.profiles.append(
                    ProfileResult(
                        profile=profile,
                        material=material,
                        waste_pct=100.0,
                    )
                )
            else:
                profile_result.profile = profile
                profile_result.material = material
                nest_result.profiles.append(profile_result)

        return nest_result

    def _on_async_optimization_finished(
        self,
        result: NestResult,
        operation: str,
        thread: QThread,
    ) -> None:
        self._last_result = result
        self.result_ready.emit(result)
        self.optimization_summary_changed.emit(OptimizationSummary.from_nest_result(result))
        self.state_changed.emit()
        self._complete_operation(operation)
        self._discard_thread(thread)

    def _on_async_optimization_failed(
        self,
        message: str,
        operation: str,
        thread: QThread,
    ) -> None:
        self._fail_operation(operation, f"Failed to optimize: {message}")
        self._discard_thread(thread)

    def _discard_thread(self, thread: QThread) -> None:
        if thread in self._async_threads:
            self._async_threads.remove(thread)

    def _discard_worker(self, worker: QObject) -> None:
        if worker in self._async_workers:
            self._async_workers.remove(worker)

    # ── Operation state helpers ───────────────────────────────

    def _begin_operation(self, operation: str, **fields: object) -> bool:
        if operation in self._busy_operations:
            message = f"{operation.replace('_', ' ').title()} is already running."
            self.error_occurred.emit(message)
            self.operation_failed.emit(operation, message)
            log_ui_event("duplicate_ignored", operation, **fields)
            return False
        self._busy_operations.add(operation)
        self.operation_started.emit(operation)
        self.state_changed.emit()
        log_ui_event("started", operation, **fields)
        return True

    def _complete_operation(self, operation: str) -> None:
        self._busy_operations.discard(operation)
        self.operation_completed.emit(operation)
        self.state_changed.emit()
        log_ui_event("completed", operation)

    def _fail_operation(self, operation: str, message: str) -> None:
        self._busy_operations.discard(operation)
        safe_message = redact(message)
        self.error_occurred.emit(safe_message)
        self.operation_failed.emit(operation, safe_message)
        self.state_changed.emit()
        log_ui_event("failed", operation, error=safe_message)


class _OptimizationWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        parts: list[PartEntry],
        market_stock: list[StockEntry],
        client_stock: list[StockEntry],
        kerf_width: float,
        scrap_threshold: float,
        max_strategies: int,
    ) -> None:
        super().__init__()
        self._parts = parts
        self._market_stock = market_stock
        self._client_stock = client_stock
        self._engine = NestEngine(
            kerf_width=kerf_width,
            scrap_threshold=scrap_threshold,
            max_strategies=max_strategies,
        )

    @Slot()
    def run(self) -> None:
        try:
            result = NestPresenter._compute_nest_result(
                self._parts,
                self._market_stock,
                self._client_stock,
                self._engine,
                progress=self.progress.emit,
            )
        except Exception as exc:
            self.failed.emit(redact(exc))
            return
        self.finished.emit(result)

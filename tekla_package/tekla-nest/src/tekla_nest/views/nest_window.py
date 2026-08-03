"""Main window — slim shell wiring widgets to the presenter.

M2 split: chrome, KPI strip, and status bar moved to dedicated widgets;
menu construction and file dialogs moved to ``nest_menu`` / ``nest_dialogs``.
This file now contains layout + presenter wiring only.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from tekla_common.config.app_config import get_config
from tekla_common.design_system import set_accessibility, set_action_enabled
from tekla_common.design_system.tokens import Theme
from tekla_common.i18n import available_languages, current_language, set_language, tr, tr_error

from ..presenters.nest_presenter import NestPresenter
from ..services.theme_service import ThemeService
from .color_dialog import ColorSchemaDialog
from .command_palette import CommandPalette
from .nest_dialogs import (
    prompt_export_csv,
    prompt_export_excel,
    prompt_export_pdf,
    prompt_load_image,
    prompt_load_parts_csv,
    prompt_load_stock_csv,
)
from .nest_menu import MenuBuilder, retranslate_window
from .parts_table import PartsTableWidget
from .purchase_table import PurchaseTableWidget
from .report_preview import ReportPreviewWidget
from .stock_tabs import StockTabsWidget
from .widgets.app_chrome import AppChrome
from .widgets.kpi_strip import KpiStrip
from .widgets.status_bar import AmbientStatusBar

_BLOCKING_ERROR_TOKENS = (
    "license",
    "activation",
    "fatal",
    "startup_failure",
)


def _is_blocking_error(message: str) -> bool:
    """Return True when an error is severe enough to warrant a modal."""
    lowered = message.lower()
    return any(token in lowered for token in _BLOCKING_ERROR_TOKENS)


class NestWindow(QMainWindow):
    """Main application window with 3-panel layout + menu bar."""

    def __init__(
        self,
        presenter: NestPresenter,
        theme_service: ThemeService | None = None,
    ) -> None:
        super().__init__()
        self._pres = presenter
        self._theme_service = theme_service
        self._actions: dict[str, QAction] = {}
        self._menus: dict[str, object] = {}
        self._language_actions: dict[str, QAction] = {}
        self._theme_actions: dict[Theme, QAction] = {}
        cfg = get_config()

        self.setWindowTitle(cfg.title)
        if cfg.icon_path.exists():
            self.setWindowIcon(QIcon(str(cfg.icon_path)))
        # Reactive sizing — start at a roomy default but allow the
        # window to shrink down to a usable Windows-laptop minimum
        # (1024×600 still keeps every panel reachable through the
        # splitter handles).
        self.setMinimumSize(960, 600)
        self.resize(1500, 800)

        self._parts_table = PartsTableWidget()
        self._stock_tabs = StockTabsWidget()
        self._report_preview = ReportPreviewWidget()
        self._purchase_table = PurchaseTableWidget()  # Feedback #6
        self._result_tabs = QTabWidget()
        self._result_tabs.addTab(self._report_preview, tr("report_tab"))
        self._result_tabs.addTab(self._purchase_table, tr("purchase.tab"))

        # Each panel gets a sane minimum width so a narrow resize
        # never hides controls behind the splitter handle.
        self._parts_table.setMinimumWidth(260)
        self._stock_tabs.setMinimumWidth(260)
        self._result_tabs.setMinimumWidth(280)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._parts_table)
        splitter.addWidget(self._stock_tabs)
        splitter.addWidget(self._result_tabs)
        splitter.setSizes([400, 370, 650])
        # Stretch factors distribute future width changes
        # proportionally: parts ≈ stock < result.
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        self._splitter = splitter

        central = QWidget()
        central.setObjectName("appShell")
        set_accessibility(central, "Application workspace")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._chrome = AppChrome(cfg.logo_path, cfg.title, cfg.background)
        self._kpi_strip = KpiStrip()
        layout.addWidget(self._chrome)
        layout.addWidget(self._kpi_strip)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._status = AmbientStatusBar(self)
        self.setStatusBar(self._status)

        builder = MenuBuilder(
            self,
            on_language_change=self._set_language,
            on_theme_change=self._apply_theme,
            current_theme=(theme_service.current() if theme_service else Theme.LIGHT),
            on_reduced_motion_change=self._apply_reduced_motion,
            reduced_motion_enabled=bool(getattr(cfg, "prefer_reduced_motion", False)),
        )
        result = builder.build()
        self._actions = result.actions
        self._menus = result.menus
        self._language_actions = result.language_actions
        self._theme_actions = result.theme_actions
        self._reduced_motion_action = result.reduced_motion_action

        for command_id in (
            "load_tekla",
            "load_parts_csv",
            "clear_parts",
            "auto_stock",
            "calculate",
            "export_pdf",
        ):
            action = self._actions.get(command_id)
            if action is not None:
                self._chrome.add_action(action)

        self._chrome.language_changed.connect(self._set_language)
        self._chrome.palette_requested.connect(self._open_palette)
        self._chrome.theme_toggled.connect(self._apply_theme)
        if theme_service is not None:
            self._chrome.set_theme(theme_service.current())
            theme_service.themeChanged.connect(self._on_theme_changed)
        self._chrome.set_languages(available_languages(), current_language())
        self._palette: CommandPalette | None = None
        QShortcut(QKeySequence("Ctrl+K"), self, self._open_palette)
        self._retranslate()

        # Presenter wiring
        self._pres.parts_loaded.connect(self._parts_table.set_parts)
        self._parts_table.rows_deleted.connect(self._on_parts_rows_deleted)
        self._pres.stock_loaded.connect(self._stock_tabs.add_stock)
        self._pres.stock_loaded.connect(self._on_stock_csv_loaded)
        self._pres.market_stock_replaced.connect(self._stock_tabs.set_market_stock)
        self._pres.result_ready.connect(self._on_result_ready)
        self._pres.optimization_summary_changed.connect(self._kpi_strip.set_summary)
        self._pres.report_html_ready.connect(self._report_preview.set_html)
        self._pres.error_occurred.connect(self._show_error)
        self._pres.csv_error_occurred.connect(self._show_csv_error)
        self._pres.notice.connect(self._show_notice)
        self._pres.operation_started.connect(self._on_operation_started)
        self._pres.operation_progress.connect(self._on_operation_progress)
        self._pres.operation_completed.connect(self._on_operation_completed)
        self._pres.operation_failed.connect(self._on_operation_failed)
        self._pres.state_changed.connect(self._sync_action_state)

        self._report_preview.bar_move_requested.connect(self._on_bar_move)
        self._report_preview.preview_error.connect(self._show_error)
        self._report_preview.action_requested.connect(self._on_report_action)
        self._sync_action_state()

    # ── Slots — file dialogs (thin wrappers around nest_dialogs) ─────

    def _on_load_parts_csv(self) -> None:
        prompt_load_parts_csv(self, self._pres)

    def _on_parts_rows_deleted(self, count: int) -> None:
        """Feedback #2 — sync the presenter's part list after a row delete
        from the parts table. The view is the source of truth for the
        deletion; we push the remaining rows back so the next
        optimisation sees the trimmed set.
        """
        del count  # logged elsewhere if needed
        self._pres.set_parts(self._parts_table.get_parts())
        self._sync_action_state()

    def _on_clear_parts(self) -> None:
        """Feedback #1 — confirm before discarding the entire parts list."""
        count = len(self._pres._parts)
        if count == 0:
            self._pres.clear_parts()
            return
        reply = QMessageBox.question(
            self,
            tr("dialogs.messages.clear_parts_title"),
            tr("dialogs.messages.clear_parts_body", count=count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._pres.clear_parts()

    def _on_load_stock_csv(self) -> None:
        prompt_load_stock_csv(self, self._pres)

    # ── View → Presenter sync helpers ────────────────────────────────
    #
    # The parts table and stock tabs are editable in-place. Without an
    # explicit sync, the presenter would optimize against a stale list
    # — the symptom being "no stock available" after a manual entry,
    # because the presenter saw 0 profiles when auto-stock seeded the
    # market. Every command that READS ``_pres._parts`` or
    # ``_pres._market_stock`` / ``_pres._client_stock`` must first
    # call _sync_view_to_presenter().
    def _sync_view_to_presenter(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            self._pres.set_parts(self._parts_table.get_parts())
        with contextlib.suppress(Exception):
            self._pres.set_market_stock(self._stock_tabs.get_market_stock())
            self._pres.set_client_stock(self._stock_tabs.get_client_stock())

    def _on_auto_stock(self) -> None:
        """Sync parts edits, then ask the presenter to seed default stock."""
        self._sync_view_to_presenter()
        self._pres.auto_populate_stock()

    def _on_calculate(self) -> None:
        """Sync parts + stock edits, then run optimization on the worker thread."""
        self._sync_view_to_presenter()
        self._pres.run_optimization_async()

    def _on_load_image(self) -> None:
        path = prompt_load_image(self)
        if path and self._report_preview.set_image(path):
            self._pres.set_attached_image(path)  # Feedback #8 — persist for PDF
            self._status.set_status(tr("status.image_attached"), "success")

    # ── Window lifecycle ─────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Guard against closing with an unexported optimization result."""
        if not (self._pres.has_result and not self._pres.result_exported):
            event.accept()
            return

        self.raise_()
        self.activateWindow()
        box = QMessageBox(self)
        box.setWindowTitle(tr("dialogs.messages.close_guard_title"))
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        box.setText(tr("dialogs.messages.close_guard_text"))
        pdf_btn = box.addButton(tr("dialogs.buttons.export_pdf"), QMessageBox.ButtonRole.ActionRole)
        excel_btn = box.addButton(
            tr("dialogs.buttons.export_excel"), QMessageBox.ButtonRole.ActionRole
        )
        close_btn = box.addButton(
            tr("dialogs.buttons.close_without_saving"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked == close_btn:
            event.accept()
        elif clicked == pdf_btn:
            exported = prompt_export_pdf(self, self._pres)
            if exported:
                self._status.set_status(tr("status.pdf_exported"), "success")
                event.accept()
            else:
                event.ignore()
        elif clicked == excel_btn:
            exported = prompt_export_excel(self, self._pres)
            if exported:
                self._status.set_status(tr("status.excel_exported"), "success")
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def _on_export_pdf(self) -> None:
        if prompt_export_pdf(self, self._pres):
            self._status.set_status(tr("status.pdf_exported"), "success")

    def _on_export_excel(self) -> None:
        if prompt_export_excel(self, self._pres):
            self._status.set_status(tr("status.excel_exported"), "success")

    def _on_export_csv(self) -> None:
        if prompt_export_csv(self, self._pres):
            self._status.set_status(tr("status.csv_exported"), "success")

    def _on_color_schema(self) -> None:
        cfg = get_config()
        dlg = ColorSchemaDialog(
            primary=cfg.primary_color,
            accent=cfg.accent_color,
            background=cfg.background,
            parent=self,
        )
        dlg.colors_accepted.connect(self._pres.update_theme_colors)
        dlg.exec()

    def _open_palette(self) -> None:
        if self._palette is not None and self._palette.isVisible():
            self._palette.raise_()
            self._palette.activateWindow()
            return
        self._palette = CommandPalette(self._actions, parent=self)
        self._palette.exec()

    # ── Slots — presenter signals ────────────────────────────────────

    def _on_result_ready(self, result: object) -> None:
        if hasattr(result, "profiles"):
            self._report_preview.set_report_context(result)
            self._purchase_table.set_result(result)  # Feedback #6
        self._pres.generate_report()

    def _on_bar_move(self, profile_idx: int, bar_row: int, direction: int) -> None:
        self._pres.reorder_bars(profile_idx, bar_row, bar_row + direction)

    def _on_report_action(self, action_id: str, context: dict) -> None:
        """Dispatch action_requested signals from ReportPreviewWidget."""
        if action_id == "report_filter_changed":
            self._pres.report_filter_changed(context.get("profile", ""))
        elif action_id == "request_stock":
            self._pres.request_stock(
                profile=context.get("profile", ""),
                length=float(context.get("length", 0) or 0),
                piece_count=int(context.get("piece_count", 0) or 0),
            )

    def _show_error(self, message: str) -> None:
        """Surface an error: status-bar always, modal only for blocking errors.

        Finding A fix: previously this always raised a modal
        ``QMessageBox.warning``, which could deadlock async error paths
        and block the entire UI. Now the status-bar message is the
        primary surface; a modal is only shown for truly blocking
        conditions (license / activation / fatal startup), identified
        by the ``modal:`` prefix on the message.
        """
        if not message:
            return
        localized = tr_error(message)
        self._status.set_status(localized, "error")
        if message.startswith("modal:") or _is_blocking_error(message):
            QMessageBox.warning(
                self,
                tr("dialogs.messages.error_title"),
                localized,
            )

    def _show_csv_error(self, title: str, detail: str) -> None:
        """Show a CSV / Tekla error as a modal dialog with full remediation text.

        ms-005: errors contain Fix: lines too long for the status bar.
        ms-013: raise + activate the parent window before exec() so the
        dialog is guaranteed to appear on top on Windows.
        """
        if sys.stdout is not None:
            print(f"[TEKLANEST] error dialog: {title} — {detail}", flush=True)
        self.raise_()
        self.activateWindow()
        from PySide6.QtWidgets import QApplication

        box = QMessageBox(self)
        box.setWindowTitle(tr("dialogs.messages.error_title"))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        box.setText(title)
        box.setInformativeText(detail)
        copy_btn = box.addButton(tr("dialogs.buttons.copy"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() == copy_btn:
            QApplication.clipboard().setText(f"{title}\n\n{detail}")

    def _show_notice(self, message: str) -> None:
        """Surface an informational notice on the status bar (non-modal).

        Finding B target: ``request_stock`` and similar suggestions land
        here so the user is informed without being interrupted.
        """
        if not message:
            return
        self._status.set_status(message, "success")

    def _on_stock_csv_loaded(self, entries: list) -> None:
        """Switch to the Client stock tab when CSV-sourced entries arrive."""
        if any(getattr(e, "source", "") == "Cliente" for e in entries):
            self._stock_tabs.setCurrentIndex(1)

    def _on_operation_started(self, operation: str) -> None:
        self._status.set_status(
            tr("status.operation_started", operation=self._operation_label(operation)),
            "loading",
        )
        self._sync_action_state()

    def _on_operation_progress(self, operation: str, message: str) -> None:
        self._status.set_status(tr_error(message) or self._operation_label(operation), "loading")

    def _on_operation_completed(self, operation: str) -> None:
        if operation == "theme":
            cfg = get_config()
            self._chrome.set_logo_background(cfg.background)
        self._status.set_status(
            tr("status.operation_completed", operation=self._operation_label(operation)),
            "success",
        )
        self._sync_action_state()

    def _on_operation_failed(self, operation: str, message: str) -> None:
        self._status.set_status(tr_error(message) or self._operation_label(operation), "error")
        self._sync_action_state()

    # ── Action state ─────────────────────────────────────────────────

    def _sync_action_state(self) -> None:
        busy = self._pres.is_busy
        has_parts = self._pres.has_parts
        has_stock = self._pres.has_stock
        has_result = self._pres.has_result

        wait = tr("disabled.wait")
        self._set_enabled("load_tekla", not busy, wait)
        self._set_enabled("load_parts_csv", not busy, wait)
        self._set_enabled("clear_parts", has_parts and not busy, tr("disabled.no_parts_to_clear"))
        self._set_enabled("load_stock_csv", not busy, wait)
        self._set_enabled("color_schema", not busy, wait)
        self._set_enabled("load_image", not busy, wait)
        self._set_enabled(
            "auto_stock", has_parts and not busy, tr("disabled.load_parts_before_stock")
        )
        self._set_enabled(
            "calculate",
            has_parts and has_stock and not busy,
            tr("disabled.load_parts_and_stock"),
        )
        for command_id in ("export_pdf", "export_excel", "export_csv"):
            self._set_enabled(command_id, has_result and not busy, tr("disabled.run_before_export"))

    def _set_enabled(self, command_id: str, enabled: bool, disabled_reason: str) -> None:
        action = self._actions.get(command_id)
        if action is not None:
            set_action_enabled(action, enabled, disabled_reason)

    # ── Theme ────────────────────────────────────────────────────────

    def _apply_theme(self, theme: Theme) -> None:
        """Persist the chosen theme via ``ThemeService`` and sync UI."""
        if self._theme_service is None:
            return
        self._theme_service.apply(theme)
        self._chrome.set_theme(theme)
        action = self._theme_actions.get(theme)
        if action is not None and not action.isChecked():
            action.setChecked(True)

    def _on_theme_changed(self, _resolved: Theme) -> None:
        """React to ``ThemeService.themeChanged`` — refresh the app stylesheet."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None and self._theme_service is not None:
            apply = app.setStyleSheet
            apply(self._theme_service.stylesheet())

    def _apply_reduced_motion(self, enabled: bool) -> None:
        """Toggle reduced-motion preference at runtime (no restart needed)."""
        from ..services.preferences_store import set_preference

        get_config().prefer_reduced_motion = bool(enabled)
        set_preference("prefer_reduced_motion", bool(enabled))

    # ── i18n ─────────────────────────────────────────────────────────

    def _set_language(self, code: str) -> None:
        set_language(code)
        self._retranslate()

    def _retranslate(self) -> None:
        retranslate_window(self)

    @staticmethod
    def _operation_label(operation: str) -> str:
        translated = tr(f"operations.{operation}")
        return (
            translated
            if translated != f"operations.{operation}"
            else operation.replace("_", " ").title()
        )

"""Tekla Nest license-admin desktop window."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..config.app_config import get_config
from ..design_system import (
    CommandDescriptor,
    StatusBanner,
    apply_action_descriptor,
    set_accessibility,
    set_action_enabled,
)
from ..i18n import available_languages, current_language, set_language, tr, tr_error
from ..theme import build_app_stylesheet
from ..views.widgets.toolbar import BrandedToolbar
from .api_client import AdminApiClient
from .models import LicenseRecord, format_datetime
from .widgets.create_license_dialog import CreateLicenseDialog
from .widgets.license_table import LicenseTableWidget


class _AdminOperationWorker(QObject):
    succeeded = Signal(str, object)
    failed = Signal(str, str)
    finished = Signal()

    def __init__(self, operation: str, func: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation
        self._func = func

    @Slot()
    def run(self) -> None:
        try:
            result = self._func()
        except Exception as exc:
            self.failed.emit(self._operation, str(exc))
        else:
            self.succeeded.emit(self._operation, result)
        finally:
            self.finished.emit()


class AdminWindow(QMainWindow):
    """Small GUI for non-technical license administration."""

    def __init__(self) -> None:
        super().__init__()
        self._client: AdminApiClient | None = None
        self._selected: LicenseRecord | None = None
        self._actions: dict[str, QAction] = {}
        self._language_actions: dict[str, QAction] = {}
        self._busy = False
        self._threads: list[QThread] = []
        self._workers: list[_AdminOperationWorker] = []
        self._success_handlers: dict[str, Callable[[object], None]] = {}
        self._build_ui()
        self._sync_action_state()

    def _build_ui(self) -> None:
        cfg = get_config()
        self.setWindowTitle(tr("admin.window.title"))
        if cfg.icon_path.exists():
            self.setWindowIcon(QIcon(str(cfg.icon_path)))
        self.resize(1250, 760)
        self.setMinimumSize(900, 560)

        central = QWidget()
        central.setObjectName("appShell")
        set_accessibility(central, tr("admin.window.workspace"))
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._toolbar = BrandedToolbar(
            cfg.logo_path,
            tr("admin.window.title"),
            cfg.background,
        )
        self._build_toolbar_actions()
        self._status = StatusBanner(tr("admin.status.ready"))

        layout.addWidget(self._toolbar)
        layout.addWidget(self._build_connection_panel())
        layout.addWidget(self._status)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        self._license_table = LicenseTableWidget()
        self._license_table.setMinimumWidth(380)
        self._license_table.selection_changed.connect(self._on_selection_changed)
        splitter.addWidget(self._license_table)
        detail_panel = self._build_detail_panel()
        detail_panel.setMinimumWidth(320)
        splitter.addWidget(detail_panel)
        splitter.setSizes([820, 430])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)
        self._build_menu()

    def _build_toolbar_actions(self) -> None:
        for command_id, slot in (
            ("refresh", self._refresh_licenses),
            ("create", self._open_create_dialog),
            ("status", self._fetch_selected_status),
            ("revoke", self._revoke_selected),
            ("release_all", self._release_all_selected),
        ):
            action = QAction(self)
            apply_action_descriptor(action, self._command_descriptor(command_id))
            action.triggered.connect(slot)
            self._toolbar.addAction(action)
            self._actions[command_id] = action

    def _build_menu(self) -> None:
        view_menu = self.menuBar().addMenu(tr("menus.view"))
        language_menu = view_menu.addMenu(tr("menus.language"))
        for code, name in available_languages().items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(code == current_language())
            action.triggered.connect(lambda _checked=False, lang=code: self._set_language(lang))
            language_menu.addAction(action)
            self._language_actions[code] = action

    def _build_connection_panel(self) -> QGroupBox:
        group = QGroupBox(tr("admin.connection.title"))
        self._connection_group = group
        layout = QHBoxLayout(group)
        form = QFormLayout()

        self._server_url = QLineEdit(get_config().license_server_url)
        self._server_url.setPlaceholderText(tr("admin.connection.server_placeholder"))
        set_accessibility(self._server_url, tr("admin.connection.server_url"))
        form.addRow(tr("admin.connection.server_url"), self._server_url)

        self._admin_key = QLineEdit()
        self._admin_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin_key.setPlaceholderText(tr("admin.connection.key_placeholder"))
        set_accessibility(self._admin_key, tr("admin.connection.admin_key"))
        form.addRow(tr("admin.connection.admin_key"), self._admin_key)

        layout.addLayout(form, stretch=1)

        side = QVBoxLayout()
        self._recovery_key = QCheckBox(tr("admin.connection.recovery_key"))
        self._recovery_key.setToolTip(tr("admin.connection.recovery_key_tip"))
        side.addWidget(self._recovery_key)

        self._connect_button = QPushButton(tr("admin.connection.connect"))
        self._connect_button.clicked.connect(self._connect_and_refresh)
        side.addWidget(self._connect_button)

        self._test_button = QPushButton(tr("admin.connection.test"))
        self._test_button.setProperty("role", "secondary")
        self._test_button.clicked.connect(self._connect_and_test)
        side.addWidget(self._test_button)
        side.addStretch()
        layout.addLayout(side)

        return group

    def _build_detail_panel(self) -> QGroupBox:
        group = QGroupBox(tr("admin.detail.title"))
        self._detail_group = group
        layout = QVBoxLayout(group)

        form = QFormLayout()
        self._detail_customer = QLabel("-")
        self._detail_key = QLabel("-")
        self._detail_status = QLabel("-")
        self._detail_expires = QLabel("-")
        self._detail_days = QLabel("-")
        self._detail_machines = QLabel("-")
        self._detail_last_validated = QLabel("-")
        self._detail_activated = QLabel("-")

        self._detail_rows = [
            ("admin.detail.customer", self._detail_customer),
            ("admin.detail.license_key", self._detail_key),
            ("admin.detail.status", self._detail_status),
            ("admin.detail.expires_at", self._detail_expires),
            ("admin.detail.days_remaining", self._detail_days),
            ("admin.detail.machines", self._detail_machines),
            ("admin.detail.last_validated", self._detail_last_validated),
            ("admin.detail.activated_at", self._detail_activated),
        ]
        for key, label in self._detail_rows:
            label.setTextInteractionFlags(label.textInteractionFlags() | Qt.TextSelectableByMouse)
            form.addRow(tr(key), label)
        layout.addLayout(form)

        self._machine_selector = QComboBox()
        layout.addWidget(QLabel(tr("admin.detail.machine_to_release")))
        layout.addWidget(self._machine_selector)

        actions = QVBoxLayout()
        self._copy_key_button = QPushButton(tr("admin.actions.copy_key"))
        self._copy_key_button.clicked.connect(self._copy_selected_key)
        actions.addWidget(self._copy_key_button)

        self._release_machine_button = QPushButton(tr("admin.actions.release_machine"))
        self._release_machine_button.clicked.connect(self._release_selected_machine)
        actions.addWidget(self._release_machine_button)

        layout.addLayout(actions)
        layout.addStretch()
        return group

    def _command_descriptor(self, command_id: str) -> CommandDescriptor:
        return CommandDescriptor(
            command_id=command_id,
            text=tr(f"admin.commands.{command_id}.text"),
            status_tip=tr(f"admin.commands.{command_id}.status"),
            toolbar_text=tr(f"admin.commands.{command_id}.toolbar"),
        )

    def _connect_and_refresh(self) -> None:
        if self._configure_client():
            self._refresh_licenses()

    def _connect_and_test(self) -> None:
        if self._configure_client():
            self._refresh_licenses(success_message=tr("admin.status.connection_ok"))

    def _configure_client(self) -> bool:
        server_url = self._server_url.text().strip()
        admin_key = self._admin_key.text().strip()
        if not server_url:
            self._status.set_status(tr("admin.errors.server_url_required"), "error")
            self._server_url.setFocus()
            return False
        if not server_url.startswith(("http://", "https://")):
            self._status.set_status(tr("admin.errors.server_url_invalid"), "error")
            self._server_url.setFocus()
            return False
        if not admin_key:
            self._status.set_status(tr("admin.errors.admin_key_required"), "error")
            self._admin_key.setFocus()
            return False
        self._client = AdminApiClient(server_url, admin_key)
        if self._recovery_key.isChecked():
            self._status.set_status(tr("admin.status.recovery_key_warning"), "warning")
        return True

    def _require_client(self) -> AdminApiClient | None:
        if self._client is None and not self._configure_client():
            return None
        return self._client

    def _refresh_licenses(self, success_message: str = "") -> None:
        client = self._require_client()
        if client is None:
            return
        self._run_operation(
            "refresh",
            client.list_licenses,
            lambda result: self._on_licenses_loaded(result, success_message),
        )

    def _open_create_dialog(self) -> None:
        if self._require_client() is None:
            return
        dialog = CreateLicenseDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        client = self._require_client()
        if client is None:
            return
        request = dialog.request()
        self._run_operation(
            "create",
            lambda: client.create_license(request),
            self._on_license_created,
        )

    def _fetch_selected_status(self) -> None:
        record = self._selected
        client = self._require_client()
        if record is None or client is None:
            return
        self._run_operation(
            "status",
            lambda: client.status(record.license_key),
            self._on_status_loaded,
        )

    def _revoke_selected(self) -> None:
        record = self._selected
        client = self._require_client()
        if record is None or client is None:
            return
        if record.revoked:
            self._status.set_status(tr("admin.status.already_revoked"), "warning")
            return
        if QMessageBox.question(
            self,
            tr("admin.confirm.revoke_title"),
            tr(
                "admin.confirm.revoke_message",
                customer=record.customer,
                key=record.license_key,
            ),
        ) != QMessageBox.StandardButton.Yes:
            return
        self._run_operation(
            "revoke",
            lambda: client.revoke(record.license_key),
            lambda _result: self._after_mutation(tr("admin.status.revoked")),
        )

    def _release_all_selected(self) -> None:
        record = self._selected
        client = self._require_client()
        if record is None or client is None:
            return
        if QMessageBox.question(
            self,
            tr("admin.confirm.release_all_title"),
            tr(
                "admin.confirm.release_all_message",
                customer=record.customer,
                key=record.license_key,
            ),
        ) != QMessageBox.StandardButton.Yes:
            return
        self._run_operation(
            "release_all",
            lambda: client.release(record.license_key),
            lambda _result: self._after_mutation(tr("admin.status.released")),
        )

    def _release_selected_machine(self) -> None:
        record = self._selected
        client = self._require_client()
        machine_id = str(self._machine_selector.currentData() or "")
        if record is None or client is None or not machine_id:
            return
        if QMessageBox.question(
            self,
            tr("admin.confirm.release_machine_title"),
            tr(
                "admin.confirm.release_machine_message",
                machine=machine_id,
                customer=record.customer,
            ),
        ) != QMessageBox.StandardButton.Yes:
            return
        self._run_operation(
            "release_machine",
            lambda: client.release(record.license_key, machine_id),
            lambda _result: self._after_mutation(tr("admin.status.released")),
        )

    def _copy_selected_key(self) -> None:
        if self._selected is None:
            return
        QApplication.clipboard().setText(self._selected.license_key)
        self._status.set_status(tr("admin.status.key_copied"), "success")

    def _run_operation(
        self,
        operation: str,
        func: Callable[[], object],
        on_success: Callable[[object], None],
    ) -> None:
        if self._busy:
            self._status.set_status(tr("admin.status.busy"), "warning")
            return
        self._busy = True
        self._success_handlers[operation] = on_success
        self._status.set_status(tr("admin.status.loading"), "loading")
        self._sync_action_state()

        thread = QThread(self)
        worker = _AdminOperationWorker(operation, func)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_operation_succeeded)
        worker.failed.connect(self._on_operation_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._thread_finished(thread, worker))
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    def _thread_finished(self, thread: QThread, worker: _AdminOperationWorker) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        if worker in self._workers:
            self._workers.remove(worker)
        thread.deleteLater()

    def _on_operation_succeeded(self, operation: str, result: object) -> None:
        self._busy = False
        handler = self._success_handlers.pop(operation, None)
        if handler:
            handler(result)
        self._sync_action_state()

    def _on_operation_failed(self, operation: str, message: str) -> None:
        self._busy = False
        self._success_handlers.pop(operation, None)
        self._status.set_status(tr_error(message), "error")
        self._sync_action_state()

    def _on_licenses_loaded(self, result: object, success_message: str = "") -> None:
        records = result if isinstance(result, list) else []
        self._license_table.set_records(records)
        self._status.set_status(
            success_message or tr("admin.status.loaded", count=len(records)),
            "success",
        )

    def _on_license_created(self, result: object) -> None:
        if not isinstance(result, LicenseRecord):
            return
        QApplication.clipboard().setText(result.license_key)
        QMessageBox.information(
            self,
            tr("admin.create.created_title"),
            tr(
                "admin.create.created_message",
                customer=result.customer,
                key=result.license_key,
            ),
        )
        self._status.set_status(tr("admin.status.created"), "success")
        self._refresh_licenses()

    def _on_status_loaded(self, result: object) -> None:
        if not isinstance(result, LicenseRecord):
            return
        self._license_table.replace_record(result)
        self._on_selection_changed(result)
        self._status.set_status(tr("admin.status.status_loaded"), "success")

    def _after_mutation(self, message: str) -> None:
        self._status.set_status(message, "success")
        self._refresh_licenses()

    def _on_selection_changed(self, record: object) -> None:
        self._selected = record if isinstance(record, LicenseRecord) else None
        self._update_detail()
        self._sync_action_state()

    def _update_detail(self) -> None:
        record = self._selected
        if record is None:
            for _key, label in self._detail_rows:
                label.setText("-")
            self._machine_selector.clear()
            return
        self._detail_customer.setText(record.customer)
        self._detail_key.setText(record.license_key)
        self._detail_status.setText(tr(f"admin.status_values.{record.status()}"))
        self._detail_expires.setText(format_datetime(record.expires_at))
        self._detail_days.setText(
            "-" if record.days_remaining is None else str(record.days_remaining)
        )
        self._detail_machines.setText(record.machine_usage)
        self._detail_last_validated.setText(format_datetime(record.last_validated))
        self._detail_activated.setText(format_datetime(record.activated_at))

        self._machine_selector.clear()
        for machine_id in record.machines:
            self._machine_selector.addItem(machine_id, machine_id)

    def _sync_action_state(self) -> None:
        connected = self._client is not None
        has_selection = self._selected is not None
        for command_id in ("refresh", "create"):
            self._set_enabled(command_id, connected and not self._busy)
        for command_id in ("status", "revoke", "release_all"):
            self._set_enabled(command_id, connected and has_selection and not self._busy)
        detail_enabled = connected and has_selection and not self._busy
        self._copy_key_button.setEnabled(has_selection)
        self._release_machine_button.setEnabled(
            detail_enabled and self._machine_selector.count() > 0
        )
        self._connect_button.setEnabled(not self._busy)
        self._test_button.setEnabled(not self._busy)

    def _set_enabled(self, command_id: str, enabled: bool) -> None:
        action = self._actions.get(command_id)
        if action is not None:
            set_action_enabled(action, enabled, tr("admin.status.disabled"))

    def _set_language(self, code: str) -> None:
        set_language(code)
        self._retranslate()

    def _retranslate(self) -> None:
        cfg = get_config()
        self.setWindowTitle(tr("admin.window.title"))
        self.setStyleSheet(build_app_stylesheet(cfg))
        for action in self._actions.values():
            command_id = action.objectName().replace("command-", "")
            apply_action_descriptor(action, self._command_descriptor(command_id))
        for code, action in self._language_actions.items():
            action.setText(available_languages()[code])
            action.setChecked(code == current_language())
        self._connection_group.setTitle(tr("admin.connection.title"))
        self._server_url.setPlaceholderText(tr("admin.connection.server_placeholder"))
        self._admin_key.setPlaceholderText(tr("admin.connection.key_placeholder"))
        self._recovery_key.setText(tr("admin.connection.recovery_key"))
        self._connect_button.setText(tr("admin.connection.connect"))
        self._test_button.setText(tr("admin.connection.test"))
        self._detail_group.setTitle(tr("admin.detail.title"))
        self._copy_key_button.setText(tr("admin.actions.copy_key"))
        self._release_machine_button.setText(tr("admin.actions.release_machine"))
        self._license_table.retranslate()
        self._update_detail()
        self._sync_action_state()

"""License activation dialog — shown on first launch if license_required=true."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from tekla_common.config.app_config import get_config
from tekla_common.design_system import set_accessibility
from tekla_common.i18n import tr, tr_error

from ..licensing.license_manager import LicenseError, LicenseManager


class ActivationDialog(QDialog):
    """Modal dialog that blocks until a valid license key is entered."""

    def __init__(self, manager: LicenseManager, parent=None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._activated = False
        self._activation_thread: QThread | None = None
        self._activation_worker: _ActivationWorker | None = None

        cfg = get_config()
        self.setWindowTitle(f"{cfg.title} - {tr('dialogs.activation.title_suffix')}")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        info = QLabel(tr("dialogs.activation.instructions"))
        info.setWordWrap(True)
        set_accessibility(info, tr("dialogs.activation.title_suffix"))
        layout.addWidget(info)

        # Key input
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        self._key_input.setMinimumHeight(32)
        set_accessibility(
            self._key_input,
            tr("dialogs.activation.license_key_name"),
            tr("dialogs.activation.license_key_description"),
        )
        layout.addWidget(self._key_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self._activate_btn = QPushButton(tr("dialogs.activation.activate"))
        self._activate_btn.setProperty("role", "primary")
        self._activate_btn.setDefault(True)
        self._activate_btn.clicked.connect(self._on_activate)
        set_accessibility(
            self._activate_btn,
            tr("dialogs.activation.activate_accessible"),
        )

        self._quit_btn = QPushButton(tr("dialogs.activation.quit"))
        self._quit_btn.setProperty("role", "secondary")
        self._quit_btn.clicked.connect(self.reject)
        set_accessibility(self._quit_btn, tr("dialogs.activation.quit_accessible"))

        btn_layout.addStretch()
        btn_layout.addWidget(self._quit_btn)
        btn_layout.addWidget(self._activate_btn)
        layout.addLayout(btn_layout)

        # Machine ID display (small, for support reference)
        mid_label = QLabel(tr("dialogs.activation.machine_id", machine_id=manager.machine_id[:16]))
        mid_label.setProperty("role", "helper")
        set_accessibility(
            mid_label,
            tr("dialogs.activation.machine_id_name"),
            tr("dialogs.activation.machine_id_description"),
        )
        layout.addWidget(mid_label)

    @property
    def activated(self) -> bool:
        return self._activated

    def _on_activate(self) -> None:
        key = self._key_input.text().strip()
        if not key:
            QMessageBox.warning(
                self,
                tr("dialogs.messages.error_title"),
                tr("dialogs.activation.missing_key"),
            )
            self._key_input.setFocus()
            return

        self._set_activation_busy(True)
        worker = _ActivationWorker(self._manager, key)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_activation_finished)
        worker.failed.connect(self._on_activation_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_activation_worker)
        self._activation_worker = worker
        self._activation_thread = thread
        thread.start()

    def reject(self) -> None:
        if self._activation_thread is not None and self._activation_thread.isRunning():
            return
        super().reject()

    @Slot(object)
    def _on_activation_finished(self, result: dict) -> None:
        self._activated = True
        customer = result.get("customer", "")
        expires = result.get("expires_at", "")
        QMessageBox.information(
            self,
            tr("dialogs.activation.activated_title"),
            tr(
                "dialogs.activation.activated_message",
                customer=customer,
                expires=expires,
            ),
        )
        self.accept()

    @Slot(str)
    def _on_activation_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            tr("dialogs.activation.failed_title"),
            tr_error(message),
        )
        self._set_activation_busy(False)

    @Slot()
    def _clear_activation_worker(self) -> None:
        self._activation_thread = None
        self._activation_worker = None

    def _set_activation_busy(self, busy: bool) -> None:
        self._activate_btn.setEnabled(not busy)
        self._quit_btn.setEnabled(not busy)
        self._key_input.setEnabled(not busy)
        self._activate_btn.setText(
            tr("dialogs.activation.activating") if busy else tr("dialogs.activation.activate")
        )


class _ActivationWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, manager: LicenseManager, license_key: str) -> None:
        super().__init__()
        self._manager = manager
        self._license_key = license_key

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self._manager.activate(self._license_key))
        except LicenseError as exc:
            self.failed.emit(str(exc))

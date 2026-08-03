"""Create-license dialog for the admin GUI."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)
from tekla_common.design_system import set_accessibility
from tekla_common.i18n import tr

from tekla_admin.models import CreateLicenseRequest

MAX_LICENSE_DAYS = 3650
MAX_LICENSE_MACHINES = 25


class CreateLicenseDialog(QDialog):
    """Collect customer and license limits before creating a server record."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("admin.create.title"))
        set_accessibility(self, tr("admin.create.title"))

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.customer_input = QLineEdit()
        self.customer_input.setMaxLength(200)
        set_accessibility(
            self.customer_input,
            tr("admin.create.customer"),
            tr("admin.create.customer_help"),
        )
        form.addRow(tr("admin.create.customer"), self.customer_input)

        self.days_input = QSpinBox()
        self.days_input.setRange(1, MAX_LICENSE_DAYS)
        self.days_input.setValue(365)
        set_accessibility(
            self.days_input,
            tr("admin.create.days"),
            tr("admin.create.days_help", max=MAX_LICENSE_DAYS),
        )
        form.addRow(tr("admin.create.days"), self.days_input)

        self.machines_input = QSpinBox()
        self.machines_input.setRange(1, MAX_LICENSE_MACHINES)
        self.machines_input.setValue(1)
        set_accessibility(
            self.machines_input,
            tr("admin.create.machines"),
            tr("admin.create.machines_help", max=MAX_LICENSE_MACHINES),
        )
        form.addRow(tr("admin.create.machines"), self.machines_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def request(self) -> CreateLicenseRequest:
        return CreateLicenseRequest(
            customer=self.customer_input.text().strip(),
            duration_days=self.days_input.value(),
            max_machines=self.machines_input.value(),
        )

    def accept(self) -> None:
        if not self.customer_input.text().strip():
            QMessageBox.warning(
                self,
                tr("dialogs.messages.error_title"),
                tr("admin.validation.customer_required"),
            )
            self.customer_input.setFocus()
            return
        super().accept()

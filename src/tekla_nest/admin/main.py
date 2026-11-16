"""Entry point for the Tekla Nest admin GUI."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .. import single_instance
from ..config.app_config import load_config
from ..i18n import tr
from ..theme import build_app_stylesheet
from .window import AdminWindow


def main() -> None:
    cfg = load_config()
    app = QApplication(sys.argv)
    app.setApplicationName("Tekla Nest Admin")
    app.setApplicationVersion(cfg.version)
    if not single_instance.acquire(single_instance.ADMIN_APP_MUTEX):
        QMessageBox.information(None, "Tekla Nest Admin", tr("dialogs.messages.app_already_running"))
        sys.exit(0)
    app.setStyleSheet(build_app_stylesheet(cfg))

    window = AdminWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


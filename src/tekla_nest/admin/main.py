"""Entry point for the Tekla Nest admin GUI."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ..config.app_config import load_config
from ..theme import build_app_stylesheet
from .window import AdminWindow


def main() -> None:
    cfg = load_config()
    app = QApplication(sys.argv)
    app.setApplicationName("Tekla Nest Admin")
    app.setApplicationVersion(cfg.version)
    app.setStyleSheet(build_app_stylesheet(cfg))

    window = AdminWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


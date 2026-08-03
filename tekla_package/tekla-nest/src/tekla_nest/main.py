"""Application entry point.

Usage:
    tekla-nest                  # via pyproject.toml console script
    uv run tekla-nest           # via uv
    python -m tekla_nest        # direct (uses __main__.py)
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from tekla_common.config.app_config import load_config
from tekla_common.theme import build_app_stylesheet

from .presenters.nest_presenter import NestPresenter
from .services.theme_service import ThemeService
from .views.nest_window import NestWindow

LOGGER = logging.getLogger(__name__)


def _check_license(app: QApplication) -> bool:
    """Verify or prompt for license activation.

    Returns True if the app should proceed, False to exit.
    """
    from tekla_common.config.app_config import get_config

    cfg = get_config()
    if not cfg.license_required:
        return True

    if not cfg.license_server_url:
        from tekla_common.i18n import tr, tr_error

        QMessageBox.critical(
            None,
            tr("dialogs.messages.configuration_error_title"),
            tr_error(
                "License server URL is not configured.\nSet licensing.server_url in config.yaml."
            ),
        )
        return False

    from tekla_common.i18n import tr, tr_error

    from .licensing.license_manager import LicenseError, LicenseManager

    try:
        manager = LicenseManager()
    except LicenseError as exc:
        QMessageBox.critical(
            None,
            tr("dialogs.messages.configuration_error_title"),
            tr_error(exc),
        )
        return False

    if manager.is_activated():
        try:
            manager.validate()
            return True
        except LicenseError as exc:
            QMessageBox.warning(
                None,
                tr("dialogs.messages.license_issue_title"),
                tr_error(exc),
            )
            # Fall through to activation dialog

    from .views.activation_dialog import ActivationDialog

    dlg = ActivationDialog(manager)
    dlg.exec()
    return dlg.activated


def main() -> None:
    """Launch the Nest Optimizer GUI."""
    if sys.stdout is not None:
        logging.basicConfig(
            level=logging.WARNING,
            stream=sys.stdout,
            format="[TEKLANEST %(levelname)s] %(name)s: %(message)s",
            force=True,
        )

    cfg = load_config()

    # Windows compatibility: pick the HiDPI rounding policy BEFORE the
    # QApplication is constructed. PassThrough preserves crisp text at
    # fractional scale factors (Windows 125% / 150% / 175%).
    from PySide6.QtCore import Qt as _Qt

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        _Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(cfg.title)
    app.setApplicationVersion(cfg.version)

    # Apply theme stylesheet (respects background → dark/light mode)
    app.setStyleSheet(build_app_stylesheet(cfg))

    # ThemeService — owns the user's theme choice + persists across restarts.
    theme_service = ThemeService(cfg)
    app.setStyleSheet(theme_service.stylesheet())
    theme_service.themeChanged.connect(lambda _t: app.setStyleSheet(theme_service.stylesheet()))

    # License gate — blocks UI if not activated
    if not _check_license(app):
        sys.exit(1)

    # Auto-detect Tekla provider on Windows
    part_provider = None
    if sys.platform == "win32":
        try:
            from .providers.tekla_provider import TeklaPartProvider

            part_provider = TeklaPartProvider()
        except Exception as exc:
            LOGGER.info(
                "Tekla provider unavailable; continuing with manual/CSV loading: %s",
                exc,
            )

    presenter = NestPresenter(part_provider=part_provider)
    window = NestWindow(presenter, theme_service=theme_service)
    window.show()

    # Deferred Tekla status probe — runs after the first event loop tick so
    # the window is fully rendered before the notice appears.
    if sys.platform == "win32":
        from PySide6.QtCore import QTimer

        def _probe_tekla() -> None:
            from tekla_common.i18n import tr

            from .services.tekla_api import find_tekla_bin

            try:
                if not find_tekla_bin():
                    presenter.notice.emit(tr("status.tekla_not_detected"))
            except Exception:
                pass

        QTimer.singleShot(200, _probe_tekla)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

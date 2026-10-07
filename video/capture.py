"""Headless real-app screenshots for the demo video."""
# ruff: noqa: E402,I001
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton, QWidget

import model
from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.design_system.tokens import Theme
from tekla_nest.i18n import set_language
from tekla_nest.main import LOGGER
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.providers.base_provider import PartProvider
from tekla_nest.services.theme_service import ThemeService
from tekla_nest.theme import build_app_stylesheet
from tekla_nest.views.nest_window import NestWindow


class DemoProvider(PartProvider):
    def __init__(self) -> None:
        self.project_name = "M13S demo frame"

    def get_parts(self):
        return model.parts()


def _suppress_modals() -> None:
    QMessageBox.warning = staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok)
    QMessageBox.question = staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes)
    QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok


def _wait(app: QApplication, predicate, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise TimeoutError("Timed out waiting for GUI state")


def _settle(app: QApplication, seconds: float = 0.35) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def _action_widget(window: NestWindow, command_id: str) -> QWidget:
    action = window._actions[command_id]
    for button in window.findChildren(QToolButton):
        if button.defaultAction() is action:
            return button
    for obj in action.associatedObjects():
        if isinstance(obj, QWidget):
            return obj
    raise RuntimeError(f"No visible widget for action {command_id}")


def _rect(window: NestWindow, widget: QWidget) -> list[int]:
    pos = widget.mapTo(window, QPoint(0, 0))
    return [pos.x(), pos.y(), widget.width(), widget.height()]


def _target(window: NestWindow, command_id: str) -> list[int]:
    return _rect(window, _action_widget(window, command_id))


def _ensure_chrome_action(window: NestWindow, command_id: str) -> None:
    actions = {
        button.defaultAction().objectName()
        for button in window.findChildren(QToolButton)
        if button.defaultAction()
    }
    if command_id not in actions:
        window._chrome.add_action(window._actions[command_id])


def _widget_by_object_prefix(window: NestWindow, prefix: str) -> QWidget:
    for widget in window.findChildren(QWidget):
        if widget.objectName().startswith(prefix) and widget.isVisible():
            return widget
    raise RuntimeError(f"No visible widget with objectName starting {prefix!r}")


def _has_visible_object_prefix(window: NestWindow, prefix: str) -> bool:
    try:
        _widget_by_object_prefix(window, prefix)
    except RuntimeError:
        return False
    return True


def _grab(window: NestWindow, out_dir: Path, shot_id: str, targets: dict[str, list[int]]) -> dict:
    QApplication.processEvents()
    pixmap = window.grab()
    filename = f"{shot_id}.png"
    if not pixmap.save(str(out_dir / filename)):
        raise RuntimeError(f"Failed to save {filename}")
    return {"id": shot_id, "file": filename, "targets": targets}


def _write_client_stock_csv(path: Path) -> Path:
    totals = Counter[str]()
    materials: dict[str, str] = {}
    for part in model.parts():
        totals[part.profile] += part.quantity
        materials.setdefault(part.profile, part.material)

    stock_plan = {
        "IPE220": [(6, 6000), (4, 8000), (2, 12000)],
        "IPE360": [(5, 8000), (2, 12000)],
        "IPE300": [(4, 6000), (3, 8000)],
        "CHS168.3x6.3": [(84, 8000)],
    }
    profiles = [profile for profile, _ in totals.most_common() if profile in stock_plan][:4]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["quantidade", "comprimento", "prioridade", "perfil", "material"],
            delimiter=";",
        )
        writer.writeheader()
        for profile in profiles:
            for quantity, length in stock_plan[profile]:
                writer.writerow({
                    "quantidade": quantity,
                    "comprimento": length,
                    "prioridade": 0,
                    "perfil": profile,
                    "material": materials.get(profile, ""),
                })
    return path


def capture(lang: str, theme: str, kerf_mm: float = 3.0, scrap_threshold_mm: float = 2000.0) -> Path:
    reset_config()
    cfg = load_config()
    cfg.kerf_width = kerf_mm
    cfg.scrap_threshold = scrap_threshold_mm
    set_language(lang)
    model_path = model.write_model()
    client_stock_path = _write_client_stock_csv(model_path.parent / "client_stock.csv")
    out_dir = model_path.parent / "capture" / f"{lang}-{theme}"
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance()
    if app is None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(["video-capture", "--platform", "offscreen"])
    app.setApplicationName(cfg.title)
    app.setApplicationVersion(cfg.version)
    app.setStyleSheet(build_app_stylesheet(cfg))

    _suppress_modals()
    LOGGER.disabled = True

    theme_service = ThemeService(cfg, prefs_path=out_dir / "theme-preferences.json")
    theme_service.apply(Theme.DARK if theme == "dark" else Theme.LIGHT)
    app.setStyleSheet(theme_service.stylesheet())

    presenter = NestPresenter(part_provider=DemoProvider())
    window = NestWindow(presenter, theme_service=theme_service)
    window.resize(1920, 1080)
    window.show()
    _wait(app, lambda: window.isVisible())
    _ensure_chrome_action(window, "load_stock_csv")
    window._sync_action_state()
    _settle(app)  # let the toolbar re-layout before measuring target rects

    shots: list[dict] = []
    shots.append(_grab(window, out_dir, "empty", {"load_tekla": _target(window, "load_tekla")}))

    window._actions["load_tekla"].trigger()
    _wait(app, lambda: presenter.has_parts)
    shots.append(_grab(window, out_dir, "parts_loaded", {
        "auto_stock": _target(window, "auto_stock"),
        "parts_table": _rect(window, window._parts_table),
    }))

    presenter.load_client_stock_csv(str(client_stock_path))
    _wait(app, lambda: presenter.has_stock and window._stock_tabs.currentIndex() == 1)
    shots.append(_grab(window, out_dir, "client_stock", {
        "client_stock": _target(window, "load_stock_csv"),
        "stock_tabs": _rect(window, window._stock_tabs),
    }))

    window._actions["auto_stock"].trigger()
    _wait(app, lambda: presenter.has_stock)
    window._stock_tabs.setCurrentIndex(0)
    _settle(app, 0.1)
    shots.append(_grab(window, out_dir, "market_stock", {
        "auto_stock": _target(window, "auto_stock"),
        "stock_tabs": _rect(window, window._stock_tabs),
    }))
    shots.append(_grab(window, out_dir, "stock_ready", {
        "calculate": _target(window, "calculate"),
    }))

    window._actions["calculate"].trigger()
    _wait(app, lambda: presenter.has_result and not presenter.is_busy, timeout=20.0)
    _wait(app, lambda: bool(window._report_preview._browser.toPlainText().strip()))
    _settle(app)
    shots.append(_grab(window, out_dir, "result", {
        "bars_view": _rect(window, window._report_preview._browser),
        "overall_waste": _rect(window, window._kpi_strip._cards[0]),
    }))

    window._result_tabs.setCurrentIndex(1)
    _settle(app, 0.1)
    shots.append(_grab(window, out_dir, "purchase", {
        "purchase_total": _rect(window, window._purchase_table._total_label),
        "purchase_table": _rect(window, window._purchase_table._table),
    }))

    window._result_tabs.setCurrentIndex(0)
    window._report_preview.set_insights_visible(True)
    _wait(app, lambda: window._report_preview._sidebar.isVisible())
    _wait(app, lambda: _has_visible_object_prefix(window, "insight-high_waste"))
    warning = _widget_by_object_prefix(window, "insight-high_waste")
    shots.append(_grab(window, out_dir, "insights", {
        "insights_panel": _rect(window, window._report_preview._sidebar),
        "overall_waste": _rect(window, window._kpi_strip._cards[0]),
        "insight_warning": _rect(window, warning),
    }))

    for command_id in ("export_excel", "export_csv"):
        if command_id not in {b.defaultAction().objectName() for b in window.findChildren(QToolButton) if b.defaultAction()}:
            window._chrome.add_action(window._actions[command_id])
    window._sync_action_state()
    _wait(app, lambda: _action_widget(window, "export_csv").isVisible())
    shots.append(_grab(window, out_dir, "export", {
        "export_pdf": _target(window, "export_pdf"),
        "export_excel": _target(window, "export_excel"),
        "export_csv": _target(window, "export_csv"),
    }))

    shot_data = {
        "lang": lang,
        "theme": theme,
        "size": [window.width(), window.height()],
        "part_count": sum(p.quantity for p in model.parts()),
        "member_count": len(model.members()),
        "window_title": window.windowTitle(),
        "config": {"kerf_mm": kerf_mm, "scrap_threshold_mm": scrap_threshold_mm},
        "shots": shots,
    }
    (out_dir / "shots.json").write_text(
        json.dumps(shot_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    presenter._result_exported = True
    window.close()
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("en", "pt"), required=True)
    parser.add_argument("--theme", choices=("light", "dark"), required=True)
    parser.add_argument("--kerf-width", type=float, default=3.0)
    parser.add_argument("--scrap-threshold", type=float, default=2000.0)
    args = parser.parse_args()
    print(capture(args.lang, args.theme, args.kerf_width, args.scrap_threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

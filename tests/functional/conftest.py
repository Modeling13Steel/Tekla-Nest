"""Shared fixtures for functional / journey tests.

These tests boot a real ``NestWindow + NestPresenter`` against an
offscreen ``QApplication`` and drive it through user-shaped scenarios.
Unit tests in ``tests/unit/`` cover components in isolation; functional
tests pin behaviour you can only see from the integrated app.

All fixtures here are deliberately *small* — each one does one thing —
so test files can compose what they need without surprises.
"""
from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QMessageBox

from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.i18n import set_language
from tekla_nest.presenters.nest_presenter import NestPresenter
from tekla_nest.views.nest_window import NestWindow

# ── Configuration reset ────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_global_state() -> Iterator[None]:
    """Reset config + language between every functional test."""
    reset_config()
    load_config()
    set_language("en")
    yield
    reset_config()
    set_language("en")


# ── Modal-dialog suppression ──────────────────────────────────────


@pytest.fixture(autouse=True)
def _suppress_modals(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Replace QMessageBox class methods so they never block the test.

    Returns the default-positive answer (Ok / Yes) so error and confirm
    dialogs continue with the action. Tests that care about what was
    asked should use ``modal_spy`` (below) instead.
    """
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        QMessageBox, "critical",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    yield


@pytest.fixture
def modal_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    """Capture every QMessageBox call as ``(kind, title, text)`` tuples.

    Replaces the auto-suppression for the *current test*. Yes answers
    are still returned so confirm dialogs proceed.
    """
    calls: list[tuple[str, str, str]] = []

    def _make(kind: str, return_btn):
        def _spy(*args, **kwargs):
            # Signature: (parent, title, text, buttons=..., default=...)
            title = args[1] if len(args) > 1 else kwargs.get("title", "")
            text = args[2] if len(args) > 2 else kwargs.get("text", "")
            calls.append((kind, str(title), str(text)))
            return return_btn
        return staticmethod(_spy)

    monkeypatch.setattr(QMessageBox, "warning",
                        _make("warning", QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "information",
                        _make("information", QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "critical",
                        _make("critical", QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question",
                        _make("question", QMessageBox.StandardButton.Yes))
    return calls


# ── Presenter / window ─────────────────────────────────────────────


@pytest.fixture
def presenter(qtbot) -> NestPresenter:
    """Construct a fresh presenter (no provider wired)."""
    return NestPresenter()


@pytest.fixture
def window(qtbot, presenter: NestPresenter) -> NestWindow:
    """Construct a NestWindow wired to ``presenter``.

    The window is *not* ``show()``-n by default — most tests don't need
    the screen geometry and showing slows the suite. Use
    ``window.show()`` in tests that exercise visibility.
    """
    w = NestWindow(presenter)
    qtbot.addWidget(w)
    return w


# ── Error / signal collectors ─────────────────────────────────────


class SignalCollector:
    """Records every emission from a NestPresenter for assertions."""

    def __init__(self, presenter: NestPresenter) -> None:
        self.errors: list[str] = []
        self.failed_ops: list[tuple[str, str]] = []
        self.started_ops: list[str] = []
        self.completed_ops: list[str] = []
        self.results: list[Any] = []
        self.htmls: list[str] = []
        self.notices: list[str] = []
        presenter.error_occurred.connect(self.errors.append)
        presenter.operation_failed.connect(
            lambda op, msg: self.failed_ops.append((op, msg))
        )
        presenter.operation_started.connect(self.started_ops.append)
        presenter.operation_completed.connect(self.completed_ops.append)
        presenter.result_ready.connect(self.results.append)
        presenter.report_html_ready.connect(self.htmls.append)
        presenter.notice.connect(self.notices.append)


@pytest.fixture
def collector(presenter: NestPresenter) -> SignalCollector:
    return SignalCollector(presenter)


# ── CSV builders ───────────────────────────────────────────────────


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        for r in rows:
            w.writerow(r)


@pytest.fixture
def parts_csv_factory(tmp_path: Path):
    """Build a parts CSV from arbitrary rows; returns the file path."""
    def _factory(
        rows: list[list] | None = None,
        name: str = "parts.csv",
    ) -> Path:
        path = tmp_path / name
        rows = rows or [
            [4, 3500, "C1", "HEA240", "S275JR"],
            [2, 5200, "C2", "HEA240", "S275JR"],
            [3, 2800, "C3", "IPE200", "S355JR"],
        ]
        _write_csv(
            path,
            ["Quantidade", "comprimento", "referencia", "perfil", "material"],
            rows,
        )
        return path
    return _factory


@pytest.fixture
def stock_csv_factory(tmp_path: Path):
    """Build a stock CSV; ``priority<0`` rows are client stock."""
    def _factory(
        rows: list[list] | None = None,
        name: str = "stock.csv",
    ) -> Path:
        path = tmp_path / name
        rows = rows or [
            [2, 6000, -1, "HEA240", "S275JR"],
            [3, 12000, 0, "IPE200", "S355JR"],
        ]
        _write_csv(
            path,
            ["Quantidade", "comprimento", "prioridade", "perfil", "material"],
            rows,
        )
        return path
    return _factory


@pytest.fixture
def mixed_material_parts(parts_csv_factory):
    """Parts CSV with the same profile (HEA240) in two materials.

    Pins Feedback #5 — grouping by ``(profile, material)``.
    """
    return parts_csv_factory(
        rows=[
            [4, 3500, "C1", "HEA240", "S275JR"],
            [2, 5200, "C2", "HEA240", "S275JR"],
            [3, 4000, "C3", "HEA240", "S235JR"],
            [3, 2800, "C4", "IPE200", "S355JR"],
        ],
        name="mixed.csv",
    )


# ── Journey helpers ────────────────────────────────────────────────


@pytest.fixture
def journey(window, presenter):
    """Tiny user-journey helper — composable methods that drive the UI."""

    class _Journey:
        def __init__(self) -> None:
            self.window = window
            self.presenter = presenter

        def load_parts(self, csv_path: Path) -> None:
            self.presenter.load_parts_from_csv(str(csv_path))

        def auto_stock(self) -> None:
            self.presenter.auto_populate_stock()

        def load_client_stock(self, csv_path: Path) -> None:
            self.presenter.load_client_stock_csv(str(csv_path))

        def calculate(self) -> None:
            self.presenter.run_optimization()

        def calculate_async(self, qtbot, timeout_ms: int = 3000) -> None:
            with qtbot.waitSignal(
                self.presenter.operation_completed, timeout=timeout_ms,
                check_params_cb=lambda op: op == "optimize",
            ):
                self.presenter.run_optimization_async()

        def parts_count(self) -> int:
            return len(self.window._parts_table.get_parts())

        def purchase_row_count(self) -> int:
            return self.window._purchase_table._table.rowCount()

        def report_html(self) -> str:
            return self.window._report_preview._browser.toHtml()

    return _Journey()


# ── QApplication lifecycle ─────────────────────────────────────────


@pytest.fixture(scope="session")
def qapp_args() -> list[str]:
    return ["tekla-nest-functional-tests"]


# pytest-qt provides a session-scoped ``qapp`` automatically; we only
# override args via ``qapp_args``. No further QApplication setup needed.

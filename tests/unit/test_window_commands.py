from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from tekla_nest.i18n import set_language
from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.presenters import NestPresenter
from tekla_nest.views.nest_window import NestWindow


def setup_function():
    set_language("en")


def teardown_function():
    set_language("en")


def test_window_command_availability_follows_presenter_state(qtbot):
    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)

    assert not window._actions["calculate"].isEnabled()
    assert not window._actions["export_csv"].isEnabled()

    presenter.set_parts([PartEntry(1, 3000, "A1", "HEA240", "S275")])
    assert not window._actions["calculate"].isEnabled()
    assert window._actions["auto_stock"].isEnabled()

    presenter.set_market_stock([StockEntry(1, 6000, 0, "HEA240", "S275")])
    assert window._actions["calculate"].isEnabled()

    presenter.run_optimization()
    assert window._actions["export_csv"].isEnabled()


def test_window_toolbar_exposes_high_frequency_actions(qtbot):
    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)

    toolbar_text = [action.iconText() for action in window._chrome.actions()]

    assert "Load Tekla" in toolbar_text
    assert "Load CSV" in toolbar_text
    assert "Auto Stock" in toolbar_text
    assert "Calculate" in toolbar_text
    assert "Export PDF" in toolbar_text
    assert toolbar_text.index("Load Tekla") < toolbar_text.index("Load CSV")


def test_window_language_menu_switches_labels(qtbot):
    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)

    window._set_language("pt")

    assert window._menus["language"].title() == "Idioma"
    assert window._actions["calculate"].text() == "Calcular"
    assert window._actions["load_tekla"].iconText() == "Carregar Tekla"
    assert window._actions["load_parts_csv"].iconText() == "CSV peças"
    assert window._parts_table._table_widget._filter_bar._search.placeholderText() == "Pesquisar tabela..."


def test_window_translates_error_messages(qtbot, monkeypatch):
    """Non-blocking errors go to the status bar (Finding A: no modal block)."""
    set_language("pt")
    captured: dict[str, str] = {}

    def fake_warning(_parent, title, message):
        captured["title"] = title
        captured["message"] = message
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)

    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)
    window._show_error("No parts loaded.")

    # Status bar always carries the localized error
    assert window._status.message == "Nenhuma peça carregada."
    # And no modal pops for ordinary errors (Finding A fix)
    assert "title" not in captured


def test_window_modal_for_blocking_errors(qtbot, monkeypatch):
    """License/activation/fatal errors still raise a modal (blocking)."""
    set_language("en")
    captured: dict[str, str] = {}

    def fake_warning(_parent, title, message):
        captured["title"] = title
        captured["message"] = message
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)

    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)
    window._show_error("license invalid")

    assert "title" in captured  # modal fired
    assert window._status.message == "license invalid"


def test_window_notice_uses_status_bar_not_modal(qtbot, monkeypatch):
    """Finding B: notice signal must not raise a modal."""
    set_language("en")
    fired = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *a, **kw: fired.append("modal") or QMessageBox.StandardButton.Ok,
    )

    presenter = NestPresenter()
    window = NestWindow(presenter)
    qtbot.addWidget(window)
    presenter.notice.emit("Heads up: stock low.")

    assert fired == []  # no modal
    assert window._status.message == "Heads up: stock low."

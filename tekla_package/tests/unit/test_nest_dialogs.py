"""M2: nest_dialogs — QFileDialog-mocked smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from tekla_nest.views import nest_dialogs


@pytest.fixture
def fake_file_dialog(monkeypatch):
    open_calls: list[tuple] = []
    save_calls: list[tuple] = []

    def fake_open(parent, title, default, file_filter):
        open_calls.append((title, file_filter))
        return ("/tmp/pretend.csv", "")

    def fake_save(parent, title, default, file_filter):
        save_calls.append((title, file_filter))
        return ("/tmp/pretend.out", "")

    monkeypatch.setattr(nest_dialogs.QFileDialog, "getOpenFileName", fake_open)
    monkeypatch.setattr(nest_dialogs.QFileDialog, "getSaveFileName", fake_save)
    monkeypatch.setattr(nest_dialogs.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(nest_dialogs.QInputDialog, "getText", lambda *a, **k: ("RC1", True))
    return open_calls, save_calls


def test_prompt_load_parts_csv_invokes_presenter(qtbot, fake_file_dialog):
    presenter = MagicMock()
    nest_dialogs.prompt_load_parts_csv(None, presenter)
    presenter.load_parts_from_csv.assert_called_once_with("/tmp/pretend.csv")


def test_prompt_load_stock_csv_invokes_presenter(qtbot, fake_file_dialog):
    presenter = MagicMock()
    nest_dialogs.prompt_load_stock_csv(None, presenter)
    presenter.load_client_stock_csv.assert_called_once_with("/tmp/pretend.csv")


def test_prompt_load_image_returns_path(qtbot, fake_file_dialog):
    assert nest_dialogs.prompt_load_image(None) == "/tmp/pretend.csv"


def test_prompt_export_pdf_returns_path_on_success(qtbot, fake_file_dialog):
    presenter = MagicMock()
    presenter.export_pdf.return_value = True
    assert nest_dialogs.prompt_export_pdf(None, presenter) == "/tmp/pretend.out"


def test_prompt_export_pdf_returns_empty_on_failure(qtbot, fake_file_dialog):
    presenter = MagicMock()
    presenter.export_pdf.return_value = False
    assert nest_dialogs.prompt_export_pdf(None, presenter) == ""


def test_prompt_export_excel_returns_path_on_success(qtbot, fake_file_dialog):
    presenter = MagicMock()
    presenter.export_excel.return_value = True
    assert nest_dialogs.prompt_export_excel(None, presenter) == "/tmp/pretend.out"


def test_prompt_export_csv_returns_path_on_success(qtbot, fake_file_dialog):
    presenter = MagicMock()
    presenter.export_csv.return_value = True
    assert nest_dialogs.prompt_export_csv(None, presenter) == "/tmp/pretend.out"


def test_prompt_handles_cancel(qtbot, monkeypatch):
    monkeypatch.setattr(nest_dialogs.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr(nest_dialogs.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr(nest_dialogs.QInputDialog, "getText", lambda *a, **k: ("", True))
    presenter = MagicMock()
    nest_dialogs.prompt_load_parts_csv(None, presenter)
    nest_dialogs.prompt_load_stock_csv(None, presenter)
    assert presenter.load_parts_from_csv.call_count == 0
    assert nest_dialogs.prompt_load_image(None) == ""
    assert nest_dialogs.prompt_export_pdf(None, presenter) == ""
    assert nest_dialogs.prompt_export_excel(None, presenter) == ""
    assert nest_dialogs.prompt_export_csv(None, presenter) == ""

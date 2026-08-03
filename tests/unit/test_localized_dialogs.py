from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QPushButton

from tekla_nest.i18n import set_language
from tekla_nest.views.activation_dialog import ActivationDialog
from tekla_nest.views.color_dialog import ColorSchemaDialog


def setup_function():
    set_language("en")


def teardown_function():
    set_language("en")


class _FakeLicenseManager:
    machine_id = "0123456789abcdef0123456789abcdef"

    def activate(self, _key: str) -> dict[str, str]:
        return {"customer": "ACME", "expires_at": "2099-01-01"}


def test_color_dialog_uses_portuguese_labels(qtbot):
    set_language("pt")

    dialog = ColorSchemaDialog("#1d4ed8", "#0f766e", "#f6f8fb")
    qtbot.addWidget(dialog)

    button_text = {button.text() for button in dialog.findChildren(QPushButton)}
    assert dialog.windowTitle() == "Esquema de cores"
    assert "Aplicar" in button_text
    assert "Cancelar" in button_text


def test_activation_dialog_uses_portuguese_labels(qtbot):
    set_language("pt")

    dialog = ActivationDialog(_FakeLicenseManager())
    qtbot.addWidget(dialog)

    assert dialog.windowTitle().endswith("Ativação")
    assert dialog._activate_btn.text() == "Ativar"
    assert dialog._quit_btn.text() == "Sair"


def test_activation_dialog_translates_license_errors(qtbot, monkeypatch):
    set_language("pt")
    captured: dict[str, str] = {}

    def fake_critical(_parent, title, message):
        captured["title"] = title
        captured["message"] = message
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", fake_critical)

    dialog = ActivationDialog(_FakeLicenseManager())
    qtbot.addWidget(dialog)
    dialog._on_activation_failed(
        "Cannot reach the license server.\n"
        "Internet access is required for first-time activation."
    )

    assert captured["title"] == "Falha na ativação"
    assert captured["message"].startswith("Não foi possível contactar")

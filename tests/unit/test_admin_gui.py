from __future__ import annotations

from datetime import UTC, datetime, timedelta

from PySide6.QtWidgets import QMessageBox

from tekla_nest.admin.models import LicenseRecord
from tekla_nest.admin.widgets.license_table import LicenseTableWidget
from tekla_nest.admin.window import AdminWindow
from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.i18n import set_language, tr


def setup_function():
    reset_config()
    load_config("/tmp/nonexistent_admin_gui_config.yaml")
    set_language("en")


def teardown_function():
    set_language("en")
    reset_config()


def test_license_record_status_values():
    now = datetime(2030, 1, 1, tzinfo=UTC)

    assert LicenseRecord("key", "Acme", revoked=True).status(now) == "revoked"
    assert (
        LicenseRecord(
            "key",
            "Acme",
            expires_at=now - timedelta(days=1),
        ).status(now)
        == "expired"
    )
    assert LicenseRecord("key", "Acme", machines=[]).status(now) == "unactivated"
    assert (
        LicenseRecord("key", "Acme", machines=["m1"], max_machines=1).status(now)
        == "full"
    )
    assert (
        LicenseRecord("key", "Acme", machines=["m1"], max_machines=2).status(now)
        == "active"
    )


def test_admin_window_starts_disconnected(qtbot):
    window = AdminWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Tekla Nest Admin"
    assert not window._actions["refresh"].isEnabled()
    assert window._status.message == "Enter the license server URL and admin key to begin."


def test_admin_window_validates_connection_fields(qtbot):
    window = AdminWindow()
    qtbot.addWidget(window)

    window._server_url.setText("")
    window._admin_key.setText("")
    window._connect_and_refresh()

    assert window._status.message == "Enter the license server URL."


def test_license_table_renders_and_filters_records(qtbot):
    table = LicenseTableWidget()
    qtbot.addWidget(table)
    table.set_records([
        LicenseRecord("active-key", "Acme", machines=["m1"], max_machines=2),
        LicenseRecord("revoked-key", "Beta", revoked=True),
    ])

    assert table._proxy_model.rowCount() == 2

    table._search.setText("Beta")
    assert table._proxy_model.rowCount() == 1

    table._search.clear()
    index = table._status_filter.findData("revoked")
    table._status_filter.setCurrentIndex(index)
    assert table._proxy_model.rowCount() == 1


def test_admin_window_uses_portuguese_labels(qtbot):
    set_language("pt")

    window = AdminWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Administração Tekla Nest"
    assert window._connection_group.title() == "Ligação"


def test_tr_accepts_key_placeholder_without_colliding():
    # Regression test: tr()'s own parameter must not be named "key", or any
    # translation string with a {key} placeholder (license key, etc.) raises
    # TypeError: tr() got multiple values for argument 'key'.
    message = tr(
        "admin.create.created_message",
        customer="Acme",
        key="abc-123",
    )
    assert "Acme" in message
    assert "abc-123" in message


def test_on_license_created_does_not_raise_and_refreshes(qtbot, monkeypatch):
    window = AdminWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    refreshed = []
    monkeypatch.setattr(window, "_refresh_licenses", lambda: refreshed.append(True))

    record = LicenseRecord("new-key", "Acme")
    window._on_license_created(record)

    assert refreshed == [True]
    assert window._status.message == "License created and copied to the clipboard."


class _FakeDeleteClient:
    def __init__(self):
        self.deleted_keys: list[str] = []

    def delete(self, license_key: str):
        self.deleted_keys.append(license_key)
        return {"license_key": license_key, "deleted": True}

    def list_licenses(self):
        return []


def test_delete_action_disabled_for_active_license(qtbot):
    window = AdminWindow()
    qtbot.addWidget(window)
    window._client = _FakeDeleteClient()

    window._selected = LicenseRecord("active-key", "Acme", machines=["m1"], max_machines=2)
    window._sync_action_state()
    assert not window._actions["delete"].isEnabled()

    window._selected = LicenseRecord("revoked-key", "Acme", revoked=True)
    window._sync_action_state()
    assert window._actions["delete"].isEnabled()

    window._selected = LicenseRecord(
        "expired-key", "Acme", expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    window._sync_action_state()
    assert window._actions["delete"].isEnabled()


def test_delete_selected_calls_client_after_confirmation(qtbot, monkeypatch):
    window = AdminWindow()
    qtbot.addWidget(window)
    client = _FakeDeleteClient()
    window._client = client
    window._selected = LicenseRecord("revoked-key", "Acme", revoked=True)

    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )

    window._delete_selected()
    qtbot.waitUntil(lambda: not window._busy, timeout=2000)

    assert client.deleted_keys == ["revoked-key"]


def test_delete_selected_blocked_for_active_license(qtbot, monkeypatch):
    window = AdminWindow()
    qtbot.addWidget(window)
    client = _FakeDeleteClient()
    window._client = client
    window._selected = LicenseRecord("active-key", "Acme", machines=["m1"], max_machines=2)

    called = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *a, **k: called.append(True) or QMessageBox.StandardButton.Yes,
    )

    window._delete_selected()

    assert not called
    assert client.deleted_keys == []
    assert window._status.message == "Only revoked or expired licenses can be deleted."

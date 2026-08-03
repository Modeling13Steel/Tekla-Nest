from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tekla_nest.admin.models import LicenseRecord
from tekla_nest.admin.widgets.license_table import LicenseTableWidget
from tekla_nest.admin.window import AdminWindow
from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.i18n import set_language


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

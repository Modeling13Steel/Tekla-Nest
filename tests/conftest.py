"""Suite-wide fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_blocking_message_box(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real ``QMessageBox.exec()`` blocks forever headless.

    NestWindow's close guard opens one when qtbot closes a window that
    still holds an unexported result at teardown, hanging the whole run.
    Return at once with nothing clicked; tests that exercise a dialog
    patch it themselves.
    """
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)

"""F12 — Phase D triage fixes (Findings A, B, C, E).

Pins the new contracts so they cannot regress:

- A: ordinary errors land on the status bar, NOT a modal.
- B: presenter.notice carries informational text on a non-error channel.
- C: CSV error messages no longer leak `Row data: {...}`.
- E: auto_populate_stock with no parts emits a notice instead of silent no-op.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tekla_nest.services.csv_loader import CsvError, load_parts_csv


def _warnings(modal_spy):
    return [c for c in modal_spy if c[0] == "warning"]


def test_a_ordinary_error_is_not_modal(window, modal_spy):
    """Finding A: non-blocking errors must NOT raise a modal dialog."""
    window._show_error("No parts loaded.")
    assert _warnings(modal_spy) == []
    msg = window._status.message or ""
    assert "No parts" in msg or "Nenhuma" in msg


def test_a_blocking_error_still_uses_modal(window, modal_spy):
    """Blocking errors (license/activation/fatal) keep their modal."""
    window._show_error("license expired")
    assert len(_warnings(modal_spy)) == 1


def test_b_notice_channel_routes_to_status_not_modal(window, presenter, modal_spy):
    """Finding B: notice signal lands on status bar, never a modal."""
    presenter.notice.emit("Stock request: 3 piece(s) of IPE200 at 6000 mm need stock.")
    assert _warnings(modal_spy) == []
    assert "Stock request" in (window._status.message or "")


def test_b_request_stock_uses_notice_not_error(presenter, collector):
    """request_stock must emit on `notice`, not `error_occurred`."""
    presenter.request_stock("IPE200", 6000.0, 3)
    assert any("Stock request" in m for m in collector.notices)
    assert collector.errors == []


def test_c_csv_error_omits_row_dict(tmp_path: Path):
    """Finding C: CSV error message must not include `Row data: {...}`."""
    bad = tmp_path / "bad_parts.csv"
    bad.write_text(
        "quantidade;comprimento;perfil\nabc;1000;IPE200\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvError) as exc_info:
        load_parts_csv(bad)
    message = str(exc_info.value)
    assert "Row data" not in message
    assert "line 2" in message
    assert "Expected" in message


def test_e_auto_populate_stock_no_parts_emits_notice(presenter, collector):
    """Finding E: auto-stock with 0 parts emits informational notice."""
    presenter.auto_populate_stock()
    assert any("Auto-stock" in m or "load parts" in m.lower() for m in collector.notices)
    assert collector.errors == []
    # No stock list emitted when there's nothing to seed
    assert collector.results == []

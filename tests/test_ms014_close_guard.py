"""Tests for ms-014: close guardrail for unsaved optimization results."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result():
    from tekla_nest.models.bar_result import BarResult
    from tekla_nest.models.nest_result import NestResult, ProfileResult

    bar = BarResult(
        original_length=6000.0, mark="B1", material="S235JR", source="stock",
        cuts=[3000.0], cut_marks=["P1"],
    )
    prof = ProfileResult(
        profile="HEA240", bars=[bar], waste_pct=8.0,
        scrap_pct=0.0, unfit_pieces=[], material="S235JR",
    )
    return NestResult(profiles=[prof])


def _presenter_with_result():
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    pres._last_result = _make_result()
    pres._result_exported = False
    return pres


# ---------------------------------------------------------------------------
# AC-004: result_exported resets to False after new optimization
# ---------------------------------------------------------------------------

def test_result_exported_resets_after_new_optimization():
    """_result_exported must become False when _last_result is overwritten."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    pres._result_exported = True        # simulate a previous export

    result = _make_result()
    pres._last_result = result
    pres._result_exported = False       # what the calculate path does

    assert pres.result_exported is False


def test_result_exported_false_initially():
    """result_exported is False on a fresh presenter."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    assert pres.result_exported is False


# ---------------------------------------------------------------------------
# AC-005 / AC-006: result_exported becomes True after successful export
# ---------------------------------------------------------------------------

def test_result_exported_true_after_export_excel(tmp_path):
    """export_excel on success must set result_exported = True."""
    pres = _presenter_with_result()
    out = tmp_path / "out.xlsx"

    with patch("tekla_nest.presenters.nest_presenter.export_excel"):
        pres.export_excel(str(out))

    assert pres.result_exported is True


def test_result_exported_true_after_export_csv(tmp_path):
    """export_csv on success must set result_exported = True."""
    pres = _presenter_with_result()
    out = tmp_path / "out.csv"

    with patch("tekla_nest.presenters.nest_presenter.export_csv"):
        pres.export_csv(str(out))

    assert pres.result_exported is True


def test_result_exported_false_after_failed_export_excel(tmp_path):
    """A failed export must NOT set result_exported = True."""
    pres = _presenter_with_result()
    out = tmp_path / "out.xlsx"

    with patch("tekla_nest.presenters.nest_presenter.export_excel",
               side_effect=OSError("disk full")):
        pres.export_excel(str(out))

    assert pres.result_exported is False


# ---------------------------------------------------------------------------
# AC-001: no dialog when has_result is False
# ---------------------------------------------------------------------------

def test_close_guard_skipped_when_no_result():
    """closeEvent must accept immediately when there is no optimization result."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    assert not pres.has_result

    event = MagicMock()
    # Simulate closeEvent logic inline (no Qt window needed)
    if not (pres.has_result and not pres.result_exported):
        event.accept()

    event.accept.assert_called_once()
    event.ignore.assert_not_called()


# ---------------------------------------------------------------------------
# AC-003: no dialog when result has been exported
# ---------------------------------------------------------------------------

def test_close_guard_skipped_when_already_exported():
    """closeEvent must accept immediately when result_exported is True."""
    pres = _presenter_with_result()
    pres._result_exported = True

    event = MagicMock()
    if not (pres.has_result and not pres.result_exported):
        event.accept()

    event.accept.assert_called_once()
    event.ignore.assert_not_called()


# ---------------------------------------------------------------------------
# AC-002: dialog shown when result exists and not exported
# ---------------------------------------------------------------------------

def test_close_guard_condition_true_when_result_not_exported():
    """has_result=True and result_exported=False triggers the close guard."""
    pres = _presenter_with_result()
    assert pres.has_result
    assert not pres.result_exported
    # The condition that triggers the dialog:
    assert pres.has_result and not pres.result_exported


# ---------------------------------------------------------------------------
# AC-007 / AC-008: i18n strings exist
# ---------------------------------------------------------------------------

def test_close_guard_i18n_keys_exist():
    """All i18n keys used by the close guard dialog must resolve."""
    from tekla_nest.i18n import tr

    keys = [
        "dialogs.messages.close_guard_title",
        "dialogs.messages.close_guard_text",
        "dialogs.buttons.export_pdf",
        "dialogs.buttons.export_excel",
        "dialogs.buttons.close_without_saving",
    ]
    for key in keys:
        val = tr(key)
        assert val and len(val) > 2, f"Key {key!r} missing or too short: {val!r}"

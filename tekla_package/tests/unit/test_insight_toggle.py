"""Tests for the insights-sidebar visibility toggle on ReportPreviewWidget.

User feedback: the suggestion panel should have a button to enable
(show) and close (hide) it. The toggle lives in the top-right of the
report preview header, beside the profile filter chips.
"""

from __future__ import annotations

from tekla_common.i18n import set_language, tr
from tekla_nest.views.report_preview import ReportPreviewWidget


def setup_function():
    set_language("en")


def teardown_function():
    set_language("en")


def test_insights_sidebar_visible_by_default(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)
    assert widget.insights_visible() is True
    # Toggle button is checked when the sidebar is showing.
    assert widget._toggle_btn.isChecked() is True
    # Default label is the "hide" verb (clicking will hide).
    assert widget._toggle_btn.text() == tr("insights.toggle.hide")


def test_toggle_button_hides_and_shows_sidebar(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)

    captured: list[bool] = []
    widget.insight_visibility_changed.connect(captured.append)

    # Simulate a click → hide.
    widget._toggle_btn.click()
    assert widget.insights_visible() is False
    assert widget._sidebar.isVisibleTo(widget) is False
    assert widget._toggle_btn.text() == tr("insights.toggle.show")
    assert captured[-1] is False

    # Click again → show.
    widget._toggle_btn.click()
    assert widget.insights_visible() is True
    assert widget._toggle_btn.text() == tr("insights.toggle.hide")
    assert captured[-1] is True


def test_programmatic_set_visibility_syncs_button(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)

    widget.set_insights_visible(False)
    assert widget._toggle_btn.isChecked() is False
    assert widget.insights_visible() is False

    widget.set_insights_visible(True)
    assert widget._toggle_btn.isChecked() is True
    assert widget.insights_visible() is True


def test_toggle_label_updates_on_language_switch(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)
    assert widget._toggle_btn.text() == tr("insights.toggle.hide")

    set_language("pt")
    widget.retranslate()
    assert widget._toggle_btn.text() == tr("insights.toggle.hide")
    # PT label is non-empty and distinct from the English one.
    assert widget._toggle_btn.text() != "Hide insights"

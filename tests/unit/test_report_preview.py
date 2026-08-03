from __future__ import annotations

from PySide6.QtCore import QUrl

from tekla_nest.models import BarResult, NestResult, ProfileResult
from tekla_nest.views.report_preview import ReportPreviewWidget


def _result_with_two_bars() -> NestResult:
    return NestResult(
        profiles=[
            ProfileResult(
                profile="HEA240",
                bars=[
                    BarResult(6000, "HEA240", "S275", "Mercado"),
                    BarResult(6000, "HEA240", "S275", "Mercado"),
                ],
            )
        ]
    )


def test_report_preview_emits_valid_reorder_command(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)
    widget.set_report_context(_result_with_two_bars())

    commands = []
    widget.bar_move_requested.connect(lambda *args: commands.append(args))

    widget._on_anchor_clicked(QUrl("reorder:///0/1/-1"))

    assert commands == [(0, 1, -1)]


def test_report_preview_rejects_stale_reorder_command(qtbot):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)
    widget.set_report_context(_result_with_two_bars())

    errors = []
    widget.preview_error.connect(errors.append)

    widget._on_anchor_clicked(QUrl("reorder:///0/0/-1"))

    assert errors
    assert "stale bar" in errors[0].lower()


def test_report_preview_missing_image_emits_error(qtbot, tmp_path):
    widget = ReportPreviewWidget()
    qtbot.addWidget(widget)
    errors = []
    widget.preview_error.connect(errors.append)

    ok = widget.set_image(str(tmp_path / "missing.png"))

    assert ok is False
    assert "not found" in errors[0].lower()

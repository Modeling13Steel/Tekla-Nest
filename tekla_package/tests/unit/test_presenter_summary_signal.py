"""Tests for ``NestPresenter.optimization_summary_changed`` signal."""

from __future__ import annotations

from PySide6.QtCore import QObject
from tekla_nest.models import (
    OptimizationSummary,
    PartEntry,
)
from tekla_nest.presenters.nest_presenter import NestPresenter


class _Collector(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[object] = []

    def collect(self, value: object) -> None:
        self.values.append(value)


def _part(length: float, mark: str) -> PartEntry:
    return PartEntry(
        quantity=1,
        length=length,
        reference=mark,
        profile="HEA240",
        material="S275JR",
    )


def test_clear_parts_emits_none(qtbot) -> None:
    pres = NestPresenter()
    collector = _Collector()
    pres.optimization_summary_changed.connect(collector.collect)

    # Seed parts so clear_parts has work to do
    pres._parts = [_part(1000.0, "M1")]
    pres.clear_parts()

    assert collector.values == [None]


def test_run_optimization_emits_summary(qtbot) -> None:
    pres = NestPresenter()
    collector = _Collector()
    pres.optimization_summary_changed.connect(collector.collect)

    pres._parts = [_part(1000.0, "M1"), _part(1500.0, "M2")]
    pres.auto_populate_stock()
    pres.run_optimization()

    # auto_populate_stock does NOT emit summary; only optimize does.
    summary_emits = [v for v in collector.values if v is not None]
    assert len(summary_emits) == 1
    summary = summary_emits[0]
    assert isinstance(summary, OptimizationSummary)
    assert summary.profile_count >= 1
    assert summary.bars_used >= 1

from __future__ import annotations

from tekla_nest.models import PartEntry, StockEntry
from tekla_nest.presenters import NestPresenter


def test_presenter_emits_operation_lifecycle(qtbot):
    presenter = NestPresenter()
    presenter.set_parts([PartEntry(1, 3000, "A1", "HEA240", "S275")])
    presenter.set_market_stock([StockEntry(1, 6000, 0, "HEA240", "S275")])

    started = []
    completed = []
    presenter.operation_started.connect(started.append)
    presenter.operation_completed.connect(completed.append)

    presenter.run_optimization()

    assert "optimize" in started
    assert "optimize" in completed


def test_presenter_rejects_duplicate_operation(qtbot):
    presenter = NestPresenter()
    presenter._busy_operations.add("optimize")

    errors = []
    failed = []
    presenter.error_occurred.connect(errors.append)
    presenter.operation_failed.connect(lambda *args: failed.append(args))

    presenter.run_optimization()

    assert errors == ["Optimize is already running."]
    assert failed == [("optimize", "Optimize is already running.")]


def test_presenter_async_optimization_completes(qtbot):
    presenter = NestPresenter()
    presenter.set_parts([PartEntry(1, 3000, "A1", "HEA240", "S275")])
    presenter.set_market_stock([StockEntry(1, 6000, 0, "HEA240", "S275")])

    completed = []
    presenter.operation_completed.connect(completed.append)

    presenter.run_optimization_async()

    qtbot.waitUntil(lambda: presenter.has_result, timeout=3000)
    assert "optimize" in completed

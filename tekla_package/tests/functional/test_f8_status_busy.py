"""F8 — Operation lifecycle (started/completed/failed)."""

from __future__ import annotations


class TestOperationLifecycle:
    def test_load_emits_started_and_completed(
        self,
        journey,
        parts_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        assert "load_parts_csv" in collector.started_ops
        assert "load_parts_csv" in collector.completed_ops

    def test_optimize_emits_started_and_completed(
        self,
        journey,
        parts_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()
        assert "optimize" in collector.started_ops
        assert "optimize" in collector.completed_ops

    def test_failed_optimize_emits_some_failure_signal(
        self,
        journey,
        collector,
    ):
        journey.calculate()
        assert collector.failed_ops or collector.errors


class TestAsyncBusyBracketing:
    def test_async_optimize_started_then_completed(
        self,
        journey,
        parts_csv_factory,
        qtbot,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate_async(qtbot, timeout_ms=5000)
        assert collector.started_ops.count("optimize") >= 1
        assert collector.completed_ops.count("optimize") >= 1

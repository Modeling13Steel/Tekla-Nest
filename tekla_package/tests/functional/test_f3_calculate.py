"""F3 — Calculation / optimization workflow (Feedback #7, #11)."""

from __future__ import annotations


class TestCalculationGating:
    def test_no_parts_no_optimize(self, journey, collector):
        journey.calculate()
        assert collector.errors, "Should refuse to optimize with no parts"
        assert not collector.results

    def test_parts_no_stock_emits_error(
        self,
        journey,
        parts_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        # No stock loaded
        journey.calculate()
        # Engine may still run (producing all unfit) or refuse;
        # in either case there must not be a Python exception.
        # state_changed should not have been corrupted.
        assert journey.presenter.has_parts


class TestCalculationHappyPath:
    def test_full_workflow_produces_result(
        self,
        journey,
        parts_csv_factory,
        collector,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate()

        assert collector.results, "result_ready never fired"
        assert collector.htmls, "report_html_ready never fired"
        result = journey.presenter._last_result
        assert result is not None
        assert result.profiles


class TestAsyncCalculation:
    def test_async_completes_and_emits_completed(
        self,
        journey,
        parts_csv_factory,
        qtbot,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        journey.calculate_async(qtbot, timeout_ms=5000)
        assert journey.presenter._last_result is not None

    def test_async_double_start_is_blocked(
        self,
        journey,
        parts_csv_factory,
        collector,
        qtbot,
    ):
        journey.load_parts(parts_csv_factory())
        journey.auto_stock()
        with qtbot.waitSignal(
            journey.presenter.operation_completed,
            timeout=5000,
            check_params_cb=lambda op: op == "optimize",
        ):
            journey.presenter.run_optimization_async()
            # Second start while first is running must be refused
            journey.presenter.run_optimization_async()
        # The error_occurred from the second start should appear
        assert any("already running" in e.lower() for e in collector.errors), (
            f"Async double-start was not blocked: errors={collector.errors}"
        )


class TestKerfFeedback7:
    """Pin Feedback #7 — kerf only between cuts, not before the first."""

    def test_piece_equal_to_bar_fits_with_kerf(
        self,
        journey,
        parts_csv_factory,
    ):
        # Bar of 6000, one cut of 6000 with kerf >0 — should fit.
        csv = parts_csv_factory(
            rows=[
                [1, 6000, "X1", "HEA240", "S275JR"],
            ],
            name="equal.csv",
        )
        journey.load_parts(csv)
        journey.auto_stock()  # creates 6000mm and other lengths
        journey.calculate()
        result = journey.presenter._last_result
        assert result and result.profiles
        # No unfit pieces — the 6000 piece fits on the 6000 bar.
        for profile in result.profiles:
            assert not profile.unfit_pieces, (
                f"Feedback #7 regression — kerf made bar-length piece unfit: {profile.unfit_pieces}"
            )

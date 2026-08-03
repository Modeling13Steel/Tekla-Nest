"""Unit tests for the NestPresenter (MVP glue layer)."""

from __future__ import annotations

import pytest
from tekla_common.config.app_config import load_config, reset_config
from tekla_nest.models import NestResult, PartEntry, StockEntry
from tekla_nest.presenters import NestPresenter
from tekla_nest.providers import ManualPartProvider


@pytest.fixture(autouse=True)
def _reset_cfg():
    reset_config()
    load_config()
    yield
    reset_config()


def _sample_parts() -> list[PartEntry]:
    return [
        PartEntry(quantity=4, length=3500, reference="C1", profile="HEA240", material="S275JR"),
        PartEntry(quantity=2, length=5200, reference="C2", profile="HEA240", material="S275JR"),
        PartEntry(quantity=3, length=2800, reference="C3", profile="IPE200", material="S355JR"),
    ]


# ── Part loading ─────────────────────────────────────────────


class TestPartLoading:
    def test_load_from_manual_provider(self, qtbot):
        provider = ManualPartProvider()
        provider.set_parts(_sample_parts())
        presenter = NestPresenter(part_provider=provider)

        signals = []
        presenter.parts_loaded.connect(signals.append)
        presenter.load_parts_from_provider()

        assert len(signals) == 1
        assert len(signals[0]) == 3

    def test_load_from_csv(self, qtbot, tmp_path):
        csv = tmp_path / "parts.csv"
        csv.write_text(
            "Quantidade;comprimento;referencia;perfil;material\n3;2500;C1;HEA240;S275JR\n",
            encoding="utf-8",
        )
        presenter = NestPresenter()

        signals = []
        presenter.parts_loaded.connect(signals.append)
        presenter.load_parts_from_csv(str(csv))

        assert len(signals) == 1
        assert signals[0][0].quantity == 3

    def test_load_csv_bad_path_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.load_parts_from_csv("/tmp/nonexistent_xyz.csv")

        assert len(errors) == 1
        assert "not found" in errors[0].lower() or "failed" in errors[0].lower()

    def test_no_provider_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.load_parts_from_provider()

        assert len(errors) == 1
        assert "no part provider" in errors[0].lower()

    def test_set_parts_directly(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        # No signal emitted for set_parts; it's a direct setter
        # Verify the parts are stored by running optimization
        assert presenter._parts == _sample_parts()


# ── Stock loading ────────────────────────────────────────────


class TestStockLoading:
    def test_auto_populate_stock(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())

        # auto_populate_stock now emits market_stock_replaced (not stock_loaded)
        # so that repeated calls replace rather than append.
        signals = []
        presenter.market_stock_replaced.connect(signals.append)
        presenter.auto_populate_stock()

        assert len(signals) == 1
        # HEA240/S275JR → 6 lengths, IPE200/S355JR → 6 lengths (one pair each)
        assert len(signals[0]) == 12

    def test_load_client_stock_csv(self, qtbot, tmp_path):
        csv = tmp_path / "stock.csv"
        csv.write_text(
            "Quantidade;comprimento;prioridade;perfil;material\n5;6000;0;HEA240;S275JR\n",
            encoding="utf-8",
        )
        presenter = NestPresenter()
        signals = []
        presenter.stock_loaded.connect(signals.append)
        presenter.load_client_stock_csv(str(csv))

        assert len(signals) == 1
        assert signals[0][0].length == 6000

    def test_load_bad_stock_csv_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.load_client_stock_csv("/tmp/nonexistent_xyz.csv")

        assert len(errors) == 1

    def test_set_market_stock(self, qtbot):
        presenter = NestPresenter()
        stock = [StockEntry(10, 6100, 0, "HEA240", "S275")]
        presenter.set_market_stock(stock)
        assert len(presenter._market_stock) == 1

    def test_set_client_stock(self, qtbot):
        presenter = NestPresenter()
        stock = [StockEntry(5, 8000, 0, "HEA240", "S275", "Cliente")]
        presenter.set_client_stock(stock)
        assert len(presenter._client_stock) == 1


# ── Optimization ─────────────────────────────────────────────


class TestOptimization:
    def test_no_parts_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.run_optimization()

        assert len(errors) == 1
        assert "no parts" in errors[0].lower()

    def test_full_optimization_emits_result(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        assert len(results) == 1
        result: NestResult = results[0]
        assert len(result.profiles) == 2  # HEA240 + IPE200
        assert all(pr.waste_pct < 100 for pr in result.profiles)

    def test_optimization_per_profile(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        hea = next(p for p in result.profiles if p.profile == "HEA240")
        ipe = next(p for p in result.profiles if p.profile == "IPE200")
        assert len(hea.bars) > 0
        assert len(ipe.bars) > 0

    def test_client_stock_used_first(self, qtbot):
        """Client stock with priority boost should be consumed before market."""
        presenter = NestPresenter()
        parts = [
            PartEntry(quantity=1, length=3000, reference="A1", profile="HEA240", material="S275")
        ]
        presenter.set_parts(parts)

        # Provide one client bar and market stock
        presenter.set_client_stock([StockEntry(1, 6000, 0, "HEA240", "S275", "Cliente")])
        presenter.set_market_stock([StockEntry(100, 12000, 0, "HEA240", "S275", "Mercado")])

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        hea = next(p for p in result.profiles if p.profile == "HEA240")
        # Should use the 6000mm client bar, not the 12000mm market bar
        assert hea.bars[0].original_length == 6000
        assert hea.bars[0].source == "Cliente"

    def test_no_stock_gives_100_waste(self, qtbot):
        presenter = NestPresenter()
        parts = [PartEntry(1, 3000, "A1", "CUSTOM_UNKNOWN_PROFILE", "S275")]
        presenter.set_parts(parts)
        # Don't populate stock → empty

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        assert result.profiles[0].waste_pct == 100.0


# ── Report ───────────────────────────────────────────────────


class TestReport:
    def test_no_result_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.generate_report()

        assert len(errors) == 1
        assert "no results" in errors[0].lower()

    def test_generate_report_after_optimization(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()
        presenter.run_optimization()

        html_signals = []
        presenter.report_html_ready.connect(html_signals.append)
        presenter.generate_report()

        assert len(html_signals) == 1
        html = html_signals[0]
        assert "<html" in html.lower()
        assert "HEA240" in html


# ── Private helpers ──────────────────────────────────────────


class TestExpandParts:
    def test_expand_single_entry(self):
        parts = [
            PartEntry(quantity=3, length=2500, reference="C1", profile="HEA240", material="S275")
        ]
        pieces = NestPresenter._expand_parts(parts)
        assert len(pieces) == 3
        assert all(p.length == 2500 for p in pieces)
        assert all(p.mark == "C1" for p in pieces)

    def test_expand_multiple_entries(self):
        parts = [
            PartEntry(2, 3000, "A", "HEA", "S275"),
            PartEntry(1, 5000, "B", "HEA", "S275"),
        ]
        pieces = NestPresenter._expand_parts(parts)
        assert len(pieces) == 3


class TestBuildStock:
    def test_client_gets_priority_boost(self, qtbot):
        presenter = NestPresenter()
        presenter.set_client_stock([StockEntry(1, 6000, 0, "HEA240", "S275", "Cliente")])
        presenter.set_market_stock([StockEntry(1, 12000, 0, "HEA240", "S275", "Mercado")])
        parts = [PartEntry(1, 3000, "A1", "HEA240", "S275")]
        bars = presenter._build_stock("HEA240", parts)

        # Client bar should come first (priority -1000)
        assert bars[0].source == "Cliente"
        assert bars[1].source == "Mercado"

    def test_material_fallback(self, qtbot):
        presenter = NestPresenter()
        presenter.set_market_stock(
            [
                StockEntry(1, 6000, 0, "HEA240", "", "Mercado")  # no material
            ]
        )
        parts = [PartEntry(1, 3000, "A1", "HEA240", "S355")]
        bars = presenter._build_stock("HEA240", parts)

        assert bars[0].material == "S355"  # falls back to part's material

    def test_case_insensitive_profile_match(self, qtbot):
        presenter = NestPresenter()
        presenter.set_market_stock([StockEntry(1, 6000, 0, "hea240", "", "Mercado")])
        parts = [PartEntry(1, 3000, "A1", "HEA240", "S275")]
        bars = presenter._build_stock("HEA240", parts)
        assert len(bars) == 1

    def test_unrelated_profile_excluded(self, qtbot):
        presenter = NestPresenter()
        presenter.set_market_stock(
            [
                StockEntry(1, 6000, 0, "IPE200", "S275", "Mercado"),
                StockEntry(1, 6000, 0, "HEA240", "S275", "Mercado"),
            ]
        )
        parts = [PartEntry(1, 3000, "A1", "HEA240", "S275")]
        bars = presenter._build_stock("HEA240", parts)
        assert len(bars) == 1
        assert bars[0].mark == "HEA240"

    def test_empty_stock(self, qtbot):
        presenter = NestPresenter()
        parts = [PartEntry(1, 3000, "A1", "HEA240", "S275")]
        bars = presenter._build_stock("HEA240", parts)
        assert bars == []


# ── Export ───────────────────────────────────────────────────


class TestExport:
    def _run_optimization(self, presenter):
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()
        presenter.run_optimization()

    def test_export_pdf_no_result_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.export_pdf("/tmp/test.pdf")
        assert any("no results" in e.lower() for e in errors)

    def test_export_excel_no_result_emits_error(self, qtbot):
        presenter = NestPresenter()
        errors = []
        presenter.error_occurred.connect(errors.append)
        presenter.export_excel("/tmp/test.xlsx")
        assert any("no results" in e.lower() for e in errors)


class TestReorder:
    def test_reorder_bars(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()
        presenter.run_optimization()

        assert presenter._last_result is not None
        profile = presenter._last_result.profiles[0]
        if len(profile.bars) >= 2:
            first_mark = profile.bars[0].mark
            second_mark = profile.bars[1].mark
            presenter.reorder_bars(0, 0, 1)
            assert profile.bars[0].mark == second_mark
            assert profile.bars[1].mark == first_mark

    def test_reorder_out_of_bounds_is_noop(self, qtbot):
        presenter = NestPresenter()
        presenter.set_parts(_sample_parts())
        presenter.auto_populate_stock()
        presenter.run_optimization()

        bar_count = len(presenter._last_result.profiles[0].bars)
        presenter.reorder_bars(0, 0, -1)  # move up from first → out of bounds
        assert len(presenter._last_result.profiles[0].bars) == bar_count


class TestThemeColors:
    def test_update_theme_colors(self, qtbot):
        from tekla_common.config.app_config import get_config

        presenter = NestPresenter()
        presenter.update_theme_colors("#ff0000", "#00ff00", "#0000ff")
        cfg = get_config()
        assert cfg.primary_color == "#ff0000"
        assert cfg.accent_color == "#00ff00"
        assert cfg.background == "#0000ff"


class TestMaterialGrouping:
    """Feedback #5 — same profile in different materials must produce one
    ProfileResult per (profile, material) pair, each nested against its
    own material stock. Old code collapsed them and silently picked
    whichever material the build returned first."""

    def test_same_profile_two_materials_yield_two_profile_results(self, qtbot):
        presenter = NestPresenter()
        parts = [
            PartEntry(quantity=1, length=3000, reference="A1", profile="HEA240", material="S235JR"),
            PartEntry(quantity=1, length=3000, reference="B1", profile="HEA240", material="S275JR"),
        ]
        presenter.set_parts(parts)
        presenter.set_market_stock(
            [
                StockEntry(10, 6000, 0, "HEA240", "S235JR", "Mercado"),
                StockEntry(10, 6000, 0, "HEA240", "S275JR", "Mercado"),
            ]
        )

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        assert len(result.profiles) == 2
        materials = {pr.material for pr in result.profiles}
        assert materials == {"S235JR", "S275JR"}
        # Each ProfileResult carries the correct material on its bars too.
        for pr in result.profiles:
            assert pr.profile == "HEA240"
            assert all(bar.material == pr.material for bar in pr.bars)

    def test_material_specific_stock_does_not_leak(self, qtbot):
        """A part of HEA240/S275JR must NOT consume HEA240/S235JR stock."""
        presenter = NestPresenter()
        parts = [
            PartEntry(quantity=1, length=3000, reference="X1", profile="HEA240", material="S275JR"),
        ]
        presenter.set_parts(parts)
        presenter.set_market_stock(
            [
                StockEntry(10, 6000, 0, "HEA240", "S235JR", "Mercado"),
            ]
        )

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        assert len(result.profiles) == 1
        pr = result.profiles[0]
        # No S275JR stock available → the piece is unfit or waste=100%.
        assert pr.material == "S275JR"
        assert pr.waste_pct == 100.0 or pr.has_unfit_pieces

    def test_same_profile_different_materials_do_not_share_bars(self, qtbot):
        """Two pieces (same profile, different material) on bars sized to fit
        only one piece each — neither should "steal" the other's bar."""
        presenter = NestPresenter()
        parts = [
            PartEntry(quantity=1, length=5000, reference="A1", profile="HEA240", material="S235JR"),
            PartEntry(quantity=1, length=5000, reference="B1", profile="HEA240", material="S275JR"),
        ]
        presenter.set_parts(parts)
        presenter.set_market_stock(
            [
                StockEntry(1, 6000, 0, "HEA240", "S235JR", "Mercado"),
                StockEntry(1, 6000, 0, "HEA240", "S275JR", "Mercado"),
            ]
        )

        results = []
        presenter.result_ready.connect(results.append)
        presenter.run_optimization()

        result: NestResult = results[0]
        assert len(result.profiles) == 2
        for pr in result.profiles:
            assert not pr.has_unfit_pieces
            assert len(pr.bars) == 1
            assert pr.bars[0].material == pr.material

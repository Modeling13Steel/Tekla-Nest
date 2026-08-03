"""F1 — Parts loading & management (Feedback #1, #2).

Functional tests for the parts side of the workflow. Each test boots
the real ``NestWindow`` + ``NestPresenter`` and drives the parts table
through user-shaped scenarios.

Findings pinned here from Phase-A repro:
* Finding D — presenter state must stay clean when a CSV load fails.
* Finding C — error messages should arrive via ``error_occurred`` with
  a single readable line (not a stack-trace wall).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

# ── Happy path ───────────────────────────────────────────────────


class TestLoadPartsHappyPath:
    def test_loads_csv_populates_table_and_state(
        self, journey, parts_csv_factory, collector,
    ):
        csv_path = parts_csv_factory()
        journey.load_parts(csv_path)

        assert journey.presenter.has_parts
        assert journey.parts_count() == 3
        assert collector.errors == []
        assert "load_parts_csv" in collector.completed_ops

    def test_load_replaces_existing_parts(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory(name="a.csv"))
        assert journey.parts_count() == 3

        journey.load_parts(parts_csv_factory(
            rows=[[1, 1000, "X1", "HEA200", "S275JR"]],
            name="b.csv",
        ))
        # Replace, never append
        assert journey.parts_count() == 1


# ── Error paths ──────────────────────────────────────────────────


class TestLoadPartsErrorPaths:
    def test_missing_file_emits_error_does_not_crash(
        self, journey, tmp_path: Path, collector,
    ):
        missing = tmp_path / "nope.csv"

        journey.load_parts(missing)

        assert collector.errors, "error_occurred should fire"
        assert collector.failed_ops, "operation_failed should fire"
        assert not journey.presenter.has_parts

    def test_malformed_row_leaves_parts_list_empty(
        self, journey, tmp_path: Path, collector,
    ):
        bad = tmp_path / "bad.csv"
        with open(bad, "w", encoding="utf-8") as f:
            f.write("Quantidade;comprimento;referencia;perfil;material\n")
            f.write("abc;3500;C1;HEA240;S275JR\n")

        journey.load_parts(bad)

        # Finding D — failed load must NOT leave half-state behind.
        assert journey.parts_count() == 0
        assert not journey.presenter.has_parts
        assert collector.errors

    def test_malformed_row_does_not_lose_previously_loaded_parts(
        self, journey, parts_csv_factory, tmp_path: Path, collector,
    ):
        # Load good first…
        journey.load_parts(parts_csv_factory(name="good.csv"))
        before = journey.parts_count()
        assert before == 3

        # …then fail with bad.
        bad = tmp_path / "bad.csv"
        with open(bad, "w", encoding="utf-8") as f:
            f.write("Quantidade;comprimento;referencia;perfil;material\n")
            f.write("abc;3500;C1;HEA240;S275JR\n")
        journey.load_parts(bad)

        # The good load must NOT have been wiped by a failed reload.
        assert journey.parts_count() == before, (
            "Failed CSV load wiped previously-good parts — state corruption"
        )

    def test_empty_csv_emits_clear_error(
        self, journey, tmp_path: Path, collector,
    ):
        empty = tmp_path / "empty.csv"
        empty.write_text("", encoding="utf-8")

        journey.load_parts(empty)

        assert collector.errors
        # Error should mention the file and what was expected
        assert any("empty.csv" in e or "empty" in e.lower()
                   for e in collector.errors)

    def test_error_message_is_single_focused_sentence(
        self, journey, tmp_path: Path, collector,
    ):
        """Finding C — error text must not be a multi-line wall.

        We allow ~3 lines (file/line context + fix hint). More than 5
        lines means we're showing the user a stack trace.
        """
        bad = tmp_path / "bad.csv"
        with open(bad, "w", encoding="utf-8") as f:
            f.write("Quantidade;comprimento;referencia;perfil;material\n")
            f.write("abc;3500;C1;HEA240;S275JR\n")

        journey.load_parts(bad)
        assert collector.errors
        line_count = collector.errors[0].count("\n") + 1
        assert line_count <= 5, (
            f"Error message has {line_count} lines:\n{collector.errors[0]}"
        )


# ── Clear parts (Feedback #1) ────────────────────────────────────


class TestClearParts:
    def test_clear_after_load_empties_table(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        assert journey.parts_count() == 3

        journey.presenter.clear_parts()

        assert journey.parts_count() == 0
        assert not journey.presenter.has_parts

    def test_clear_idempotent(self, journey, collector):
        journey.presenter.clear_parts()
        journey.presenter.clear_parts()
        # Should never error
        assert collector.errors == []

    def test_clear_resets_attached_image(
        self, journey, parts_csv_factory, tmp_path,
    ):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        journey.load_parts(parts_csv_factory())
        journey.presenter.set_attached_image(str(img))
        assert journey.presenter.attached_image_path() == str(img)

        journey.presenter.clear_parts()
        assert journey.presenter.attached_image_path() is None


# ── Row delete (Feedback #2) ─────────────────────────────────────


class TestRowDelete:
    def test_delete_key_removes_selected_row(
        self, journey, parts_csv_factory, qtbot,
    ):
        journey.load_parts(parts_csv_factory())
        table_widget = journey.window._parts_table._table_widget
        table = table_widget.table
        # Select row 0
        table.selectRow(0)
        assert table_widget.selection_count() == 1
        removed = table_widget.delete_selected_rows()
        assert removed == 1
        assert journey.parts_count() == 2

    def test_delete_with_no_selection_is_noop(
        self, journey, parts_csv_factory,
    ):
        journey.load_parts(parts_csv_factory())
        table_widget = journey.window._parts_table._table_widget
        removed = table_widget.delete_selected_rows()
        assert removed == 0
        assert journey.parts_count() == 3

    def test_delete_emits_rows_deleted_signal(
        self, journey, parts_csv_factory, qtbot,
    ):
        journey.load_parts(parts_csv_factory())
        table_widget = journey.window._parts_table._table_widget
        table_widget.table.selectRow(0)

        with qtbot.waitSignal(table_widget.rows_deleted, timeout=1000) as blocker:
            table_widget.delete_selected_rows()
        assert blocker.args == [1]

    def test_delete_syncs_presenter_state(
        self, journey, parts_csv_factory, qtbot,
    ):
        """Deleting a row in the table must update presenter._parts.

        Otherwise calculation runs on stale data.
        """
        journey.load_parts(parts_csv_factory())
        table_widget = journey.window._parts_table._table_widget
        table_widget.table.selectRow(0)
        table_widget.delete_selected_rows()
        # Pump the event loop so the rows_deleted signal reaches the window
        QApplication.processEvents()
        assert len(journey.presenter._parts) == 2, (
            "Presenter parts not synced after table row delete"
        )


# ── Pin Feedback #5 — mixed materials grouping ───────────────────


class TestMixedMaterialGrouping:
    def test_same_profile_two_materials_split_into_two_results(
        self, journey, mixed_material_parts,
    ):
        journey.load_parts(mixed_material_parts)
        journey.auto_stock()
        journey.calculate()

        result = journey.presenter._last_result
        assert result is not None
        keys = {(p.profile, p.material) for p in result.profiles}
        assert ("HEA240", "S275JR") in keys
        assert ("HEA240", "S235JR") in keys, (
            "Feedback #5 regression — HEA240 in two materials merged into one"
        )

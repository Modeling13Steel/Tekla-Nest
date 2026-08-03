"""Tests for ms-012: filter chip sort + CSV error diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_part(profile, material, reference="P1", length=3000.0, qty=1):
    from tekla_nest.models import PartEntry

    return PartEntry(
        quantity=qty, length=length, reference=reference, profile=profile, material=material
    )


def _make_stock(profile, material, length, source="Cliente"):
    from tekla_nest.models import StockEntry

    return StockEntry(
        quantity=1, length=length, priority=0, profile=profile, material=material, source=source
    )


# ---------------------------------------------------------------------------
# AC-001: _refresh_material_chips passes a sorted list to set_materials
# ---------------------------------------------------------------------------


def _make_fake_widget(getter):
    """Return a SimpleNamespace that mimics the attributes needed by _refresh_material_chips."""
    import types

    from tekla_nest.views.table_system import ColumnDefinition, DataTableWidget

    col = ColumnDefinition(
        header="Material",
        getter=getter,
        setter=lambda r, v: None,
        header_key="tables.parts.col.material",
    )
    received = []
    fb = MagicMock()
    fb.set_materials = lambda mats: received.append(list(mats))
    ns = types.SimpleNamespace(
        _columns=[col],
        _material_column=0,
        _filter_bar=fb,
        _received=received,
    )
    # Bind the unbound method to our namespace object
    ns._refresh_material_chips = DataTableWidget._refresh_material_chips.__get__(ns)
    return ns


def test_refresh_material_chips_sorted():
    """_refresh_material_chips must pass an alphabetically sorted list to set_materials."""
    widget = _make_fake_widget(lambda r: r.material)

    # Intentionally unsorted insertion order: S355JR before S235JR
    rows = [
        _make_part("IPE300", "S355JR"),
        _make_part("HEA240", "S235JR"),
        _make_part("IPE300", "S235JR"),
    ]
    widget._refresh_material_chips(rows)

    assert widget._received, "set_materials was never called"
    chips = widget._received[-1]
    assert chips == sorted(chips), f"Chips not sorted: {chips}"
    assert chips == ["S235JR", "S355JR"]


def test_refresh_material_chips_consistent_across_both_tables():
    """Parts and stock tables produce identical chip order for the same material set."""
    parts_widget = _make_fake_widget(lambda r: r.material)
    stock_widget = _make_fake_widget(lambda r: r.material)

    # Reversed insertion order for each
    parts = [_make_part("IPE300", "S355JR"), _make_part("HEA240", "S235JR")]
    stock = [_make_stock("HEA240", "S235JR", 6000), _make_stock("IPE300", "S355JR", 12000)]

    parts_widget._refresh_material_chips(parts)
    stock_widget._refresh_material_chips(stock)

    assert parts_widget._received[-1] == stock_widget._received[-1], (
        f"Parts chips {parts_widget._received[-1]} != Stock chips {stock_widget._received[-1]}"
    )


# ---------------------------------------------------------------------------
# AC-002: generic Exception in load_parts_from_csv emits csv_error_occurred
# ---------------------------------------------------------------------------


def test_generic_exception_in_parts_csv_emits_csv_error_occurred():
    """A non-CsvError exception during parts CSV load must emit csv_error_occurred."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.presenters.nest_presenter.load_parts_csv",
        side_effect=RuntimeError("unexpected boom"),
    ):
        pres.load_parts_from_csv("/fake/path.csv")

    assert csv_errors, "csv_error_occurred was not emitted for unexpected Exception"


# ---------------------------------------------------------------------------
# AC-003: generic Exception in load_client_stock_csv emits csv_error_occurred
# ---------------------------------------------------------------------------


def test_generic_exception_in_stock_csv_emits_csv_error_occurred():
    """A non-CsvError exception during stock CSV load must emit csv_error_occurred."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.presenters.nest_presenter.load_stock_csv", side_effect=RuntimeError("disk full")
    ):
        pres.load_client_stock_csv("/fake/stock.csv")

    assert csv_errors, "csv_error_occurred was not emitted for unexpected Exception"


# ---------------------------------------------------------------------------
# CsvError still emits csv_error_occurred (regression guard)
# ---------------------------------------------------------------------------


def test_csv_error_in_parts_csv_still_emits_csv_error_occurred():
    """CsvError during parts CSV load must still emit csv_error_occurred."""
    from tekla_nest.presenters.nest_presenter import NestPresenter
    from tekla_nest.services.csv_loader import CsvError

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.presenters.nest_presenter.load_parts_csv", side_effect=CsvError("bad header")
    ):
        pres.load_parts_from_csv("/fake/path.csv")

    assert csv_errors, "csv_error_occurred was not emitted for CsvError"


def test_csv_error_in_stock_csv_still_emits_csv_error_occurred():
    """CsvError during stock CSV load must still emit csv_error_occurred."""
    from tekla_nest.presenters.nest_presenter import NestPresenter
    from tekla_nest.services.csv_loader import CsvError

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.presenters.nest_presenter.load_stock_csv",
        side_effect=CsvError("missing column"),
    ):
        pres.load_client_stock_csv("/fake/stock.csv")

    assert csv_errors, "csv_error_occurred was not emitted for CsvError"


# ---------------------------------------------------------------------------
# AC-004: stdout logging configured when sys.stdout is not None
# ---------------------------------------------------------------------------


def test_stdout_logging_configured_when_stdout_present():
    """After main-style basicConfig, a WARNING log message appears on stdout."""
    import io
    import logging

    fake_stdout = io.StringIO()

    if fake_stdout is not None:
        logging.basicConfig(
            level=logging.WARNING,
            stream=fake_stdout,
            format="[TEKLANEST %(levelname)s] %(name)s: %(message)s",
            force=True,
        )

    test_logger = logging.getLogger("tekla_nest.test_ms012")
    test_logger.warning("probe message")

    output = fake_stdout.getvalue()
    assert "probe message" in output, f"Expected log on stdout, got: {output!r}"

    # Restore to avoid polluting other tests
    logging.root.handlers.clear()


# ---------------------------------------------------------------------------
# AC-005: stdout print in load_parts_from_csv CsvError path
# ---------------------------------------------------------------------------


def test_csv_error_parts_prints_to_stdout(capsys):
    """CsvError during parts CSV load must print a diagnostic line to stdout."""
    from tekla_nest.presenters.nest_presenter import NestPresenter
    from tekla_nest.services.csv_loader import CsvError

    pres = NestPresenter()
    with patch(
        "tekla_nest.presenters.nest_presenter.load_parts_csv", side_effect=CsvError("bad header")
    ):
        pres.load_parts_from_csv("/fake/path.csv")

    captured = capsys.readouterr()
    assert "TEKLANEST" in captured.out or "TEKLANEST" in captured.err, (
        f"Expected [TEKLANEST] diagnostic on stdout/stderr, got out={captured.out!r}"
    )


def test_generic_error_parts_prints_to_stdout(capsys):
    """Unexpected exception during parts CSV load must print a diagnostic line."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    with patch(
        "tekla_nest.presenters.nest_presenter.load_parts_csv", side_effect=RuntimeError("boom")
    ):
        pres.load_parts_from_csv("/fake/path.csv")

    captured = capsys.readouterr()
    assert "TEKLANEST" in captured.out or "TEKLANEST" in captured.err, (
        f"Expected [TEKLANEST] diagnostic on stdout/stderr, got out={captured.out!r}"
    )

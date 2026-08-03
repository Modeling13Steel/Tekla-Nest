"""Tests for ms-011: CSV feedback visibility + material sort consistency."""

from __future__ import annotations

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_part(profile, material, reference="P1", length=3000.0, qty=1):
    from tekla_nest.models import PartEntry

    return PartEntry(
        quantity=qty, length=length, reference=reference, profile=profile, material=material
    )


def _make_stock(profile, material, length, source="Mercado"):
    from tekla_nest.models import StockEntry

    return StockEntry(
        quantity=1, length=length, priority=0, profile=profile, material=material, source=source
    )


# ---------------------------------------------------------------------------
# Sort helpers
# ---------------------------------------------------------------------------


def test_sort_parts_by_profile_then_material():
    from tekla_nest.presenters.nest_presenter import _sort_parts

    parts = [
        _make_part("IPE300", "S275JR"),
        _make_part("HEA240", "S355JR"),
        _make_part("HEA240", "S235JR"),
    ]
    result = _sort_parts(parts)
    assert [(p.profile, p.material) for p in result] == [
        ("HEA240", "S235JR"),
        ("HEA240", "S355JR"),
        ("IPE300", "S275JR"),
    ]


def test_sort_stock_by_profile_material_length():
    from tekla_nest.presenters.nest_presenter import _sort_stock

    stock = [
        _make_stock("IPE300", "S235JR", 12000),
        _make_stock("HEA240", "S275JR", 6000),
        _make_stock("HEA240", "S235JR", 12000),
        _make_stock("HEA240", "S235JR", 6000),
    ]
    result = _sort_stock(stock)
    assert [(s.profile, s.material, s.length) for s in result] == [
        ("HEA240", "S235JR", 6000),
        ("HEA240", "S235JR", 12000),
        ("HEA240", "S275JR", 6000),
        ("IPE300", "S235JR", 12000),
    ]


def test_parts_and_stock_same_profile_material_order():
    """After sorting, (profile, material) order in parts matches stock."""
    from tekla_nest.presenters.nest_presenter import _sort_parts, _sort_stock

    parts = [
        _make_part("IPE300", "S235JR"),
        _make_part("HEA240", "S355JR"),
        _make_part("HEA240", "S235JR"),
    ]
    stock = [
        _make_stock("IPE300", "S235JR", 6000),
        _make_stock("HEA240", "S355JR", 12000),
        _make_stock("HEA240", "S235JR", 6000),
    ]
    sorted_parts = [(p.profile, p.material) for p in _sort_parts(parts)]
    sorted_stock_keys = list(
        dict.fromkeys(  # deduplicate preserving order
            (s.profile, s.material) for s in _sort_stock(stock)
        )
    )
    assert sorted_parts == sorted_stock_keys


# ---------------------------------------------------------------------------
# CSV notice ordering: notice appears AFTER _complete_operation
# ---------------------------------------------------------------------------


def test_csv_stock_notice_emitted_after_complete_operation():
    """notice.emit must fire after _complete_operation so it is not overwritten."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    call_order: list[str] = []

    pres.operation_completed.connect(lambda op: call_order.append("completed"))
    pres.notice.connect(lambda msg: call_order.append("notice"))

    fake_entries = [_make_stock("HEA240", "S235JR", 6000, source="Cliente")]
    with patch("tekla_nest.presenters.nest_presenter.load_stock_csv", return_value=fake_entries):
        pres.load_client_stock_csv("/fake/path.csv")

    assert "completed" in call_order
    assert "notice" in call_order
    assert call_order.index("notice") > call_order.index("completed"), (
        "notice fired before operation_completed — will be overwritten by success msg"
    )


def test_csv_parts_empty_notice_emitted_after_complete_operation():
    """Empty-parts notice must fire after _complete_operation."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    call_order: list[str] = []

    pres.operation_completed.connect(lambda op: call_order.append("completed"))
    pres.notice.connect(lambda msg: call_order.append("notice"))

    with patch("tekla_nest.presenters.nest_presenter.load_parts_csv", return_value=[]):
        pres.load_parts_from_csv("/fake/path.csv")

    assert "completed" in call_order
    assert "notice" in call_order
    assert call_order.index("notice") > call_order.index("completed")


def test_load_parts_csv_returns_sorted():
    """Parts loaded from CSV are sorted by profile then material."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    received: list = []
    pres.parts_loaded.connect(lambda parts: received.extend(parts))

    raw = [
        _make_part("IPE300", "S275JR"),
        _make_part("HEA240", "S355JR"),
        _make_part("HEA240", "S235JR"),
    ]
    with patch("tekla_nest.presenters.nest_presenter.load_parts_csv", return_value=raw):
        pres.load_parts_from_csv("/fake/path.csv")

    assert [(p.profile, p.material) for p in received] == [
        ("HEA240", "S235JR"),
        ("HEA240", "S355JR"),
        ("IPE300", "S275JR"),
    ]

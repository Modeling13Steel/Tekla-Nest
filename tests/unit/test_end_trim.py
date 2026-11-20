"""'Spare 100 mm / bar' tickbox: factory bars lose ``end_trim`` mm of usable
length (uneven mill end) but are still bought and reported at full length.
Client offcuts are never trimmed.
"""
from __future__ import annotations

import pytest

from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.models import CutPiece, StockBar
from tekla_nest.services.nest_engine import NestEngine


@pytest.fixture(autouse=True)
def _cfg():
    reset_config()
    load_config("/tmp/nonexistent_config_end_trim.yaml")  # defaults: end_trim 100
    yield
    reset_config()


def _market(length: float, qty: int = 5) -> list[StockBar]:
    return [StockBar(length, "HEA240", "S275JR", "Mercado", 0) for _ in range(qty)]


def test_trim_reduces_usable_length_but_not_purchase_length():
    pieces = [CutPiece(8000, "A"), CutPiece(8000, "B")]
    r = NestEngine(end_trim=100).optimize(pieces, _market(16100))
    assert len(r.bars) == 1
    bar = r.bars[0]
    assert bar.original_length == 16100  # supplier still sells 16100
    assert bar.end_trim == 100
    assert bar.free_length == 0  # usable offcut
    assert r.waste_pct == pytest.approx(100 / 16100 * 100)  # trim counts as scrap


def test_trim_can_push_a_piece_to_the_next_bar():
    pieces = [CutPiece(8050, "A"), CutPiece(8000, "B")]
    assert len(NestEngine().optimize(pieces, _market(16100)).bars) == 1
    trimmed = NestEngine(end_trim=100).optimize(pieces, _market(16100))
    assert len(trimmed.bars) == 2 and not trimmed.unfit_pieces


def test_piece_longer_than_trimmed_bar_is_unfit():
    r = NestEngine(end_trim=100).optimize([CutPiece(16050, "A")], _market(16100))
    assert [p.mark for p in r.unfit_pieces] == ["A"]


def test_client_offcuts_are_not_trimmed():
    client = [StockBar(6000, "HEA240", "S275JR", "Cliente", -1000)]
    r = NestEngine(end_trim=100).optimize([CutPiece(6000, "A")], client + _market(12100))
    assert [(b.source, b.end_trim, b.free_length) for b in r.bars] == [("Cliente", 0.0, 0.0)]


def test_presenter_toggle_reaches_engine(qtbot):
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    assert pres._engine.end_trim == 0.0
    pres.set_end_trim(True)
    assert pres._engine.end_trim == 100.0
    pres.set_end_trim(False)
    assert pres._engine.end_trim == 0.0


def test_stock_tabs_tickbox_defaults_off(qtbot):
    from PySide6.QtWidgets import QCheckBox

    from tekla_nest.views.stock_tabs import StockTabsWidget

    w = StockTabsWidget()
    qtbot.addWidget(w)
    cb = w.findChild(QCheckBox, "endTrimCheck")
    assert cb is not None and "100" in cb.text()
    assert w.end_trim_enabled() is False
    cb.setChecked(True)
    assert w.end_trim_enabled() is True

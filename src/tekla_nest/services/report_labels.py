"""Localized labels shared by HTML, Excel, and CSV reports."""
from __future__ import annotations

from types import SimpleNamespace

from ..config.app_config import AppConfig
from ..i18n import tr

_DEFAULT_REPORT_TITLES = {"Plano de Corte", "Cut Plan", ""}


def report_labels(config: AppConfig) -> SimpleNamespace:
    """Return report labels in the current UI language."""
    title = (
        tr("report.title")
        if config.report_title in _DEFAULT_REPORT_TITLES
        else config.report_title
    )
    return SimpleNamespace(
        title=title,
        logo_alt=tr("report.logo_alt"),
        generated_at=tr("report.generated_at"),
        overall_waste=tr("report.overall_waste"),
        profiles=tr("report.profiles"),
        total_bars=tr("report.total_bars"),
        waste=tr("report.waste"),
        bar_mark=tr("report.columns.bar_mark"),
        bar_length=tr("report.columns.bar_length"),
        cuts=tr("report.columns.cuts"),
        cut_marks=tr("report.columns.cut_marks"),
        waste_mm=tr("report.columns.waste_mm"),
        material=tr("report.columns.material"),
        source=tr("report.columns.source"),
        move=tr("report.columns.move"),
        move_bar_up=tr("report.move_bar_up"),
        move_bar_down=tr("report.move_bar_down"),
        no_stock=tr("report.no_stock"),
        unfit_pieces_header=tr("report.unfit_pieces_header"),
        unfit_pieces_explain=tr("report.unfit_pieces_explain"),
        summary_sheet=tr("report.excel.summary_sheet"),
        profile=tr("report.excel.profile"),
        bars_used=tr("report.excel.bars_used"),
        waste_pct=tr("report.excel.waste_pct"),
        scrap_pct=tr("report.excel.scrap_pct"),
        total=tr("report.excel.total"),
        purchase_sheet=tr("report.excel.purchase_sheet"),
        linear_meters=tr("report.excel.linear_meters"),
        prep_header=tr("report.prep.header"),
        prep_bar=tr("report.prep.bar"),
        prep_total=tr("report.prep.total"),
        site_image_sheet=tr("report.excel.site_image_sheet"),
        project_name_label=tr("report.project_name_label"),
        milestone_label=tr("report.milestone_label"),
    )

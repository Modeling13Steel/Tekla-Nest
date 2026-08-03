"""CSV report generation — one file mirroring the PDF/HTML report layout.

Uses only the Python standard library (csv module).
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from tekla_common.config.app_config import get_config

from ..models import NestResult
from .report_labels import report_labels


def _bar_row(bar, idx: int, cfg) -> list:
    """Build a single CSV row for a bar result."""
    row: list = [
        idx,
        bar.mark,
        int(bar.original_length),
        ", ".join(str(int(c)) for c in bar.cuts),
        ", ".join(bar.cut_marks),
        int(bar.free_length),
    ]
    if cfg.show_material:
        row.append(bar.material)
    if cfg.show_stock_source:
        row.append(bar.source)
    return row


def _col_headers(cfg, labels) -> list[str]:
    """Build column header list based on config flags."""
    headers = [
        "#",
        labels.bar_mark,
        labels.bar_length,
        labels.cuts,
        labels.cut_marks,
        labels.waste_mm,
    ]
    if cfg.show_material:
        headers.append(labels.material)
    if cfg.show_stock_source:
        headers.append(labels.source)
    return headers


def export_csv(
    result: NestResult,
    output_path: str | Path,
    scope: frozenset[tuple[str, str]] | None = None,
) -> Path:
    """Write nesting results to a CSV file matching the PDF report layout.

    Layout:
      - Header rows (title, company, date)
      - Summary row (overall waste, profile count, total bars)
      - Per-profile sections with profile header + bar table

    ``scope`` (feedback v2 #2.1) filters the result before rendering.

    Returns the resolved output path.
    """
    cfg = get_config()
    labels = report_labels(cfg)
    from .bar_aggregation import filter_result

    result = filter_result(result, scope)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    headers = _col_headers(cfg, labels)
    ncols = len(headers)

    def pad(n: int) -> list[str]:
        return [""] * (ncols - n)

    total_bars = sum(len(p.bars) for p in result.profiles)

    # utf-8-sig writes a BOM so Excel on Windows opens the file with
    # the correct codec instead of mis-decoding accented characters.
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")

        # ── Header ────────────────────────────────────────────
        writer.writerow([labels.title] + pad(1))
        if cfg.company_name:
            writer.writerow([cfg.company_name] + pad(1))
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M")] + pad(1))
        writer.writerow(pad(0))

        # ── Summary ───────────────────────────────────────────
        writer.writerow(
            [
                f"{labels.overall_waste}: {result.overall_waste_pct:.2f}%",
                f"{labels.profiles}: {len(result.profiles)}",
                f"{labels.total_bars}: {total_bars}",
            ]
            + pad(3)
        )
        writer.writerow(pad(0))

        # ── Per-profile sections ──────────────────────────────
        for prof in result.profiles:
            profile_header = f"{prof.profile} / {prof.material}" if prof.material else prof.profile
            writer.writerow([f"{profile_header} - {labels.waste}: {prof.waste_pct:.2f}%"] + pad(1))
            writer.writerow(headers)

            if prof.bars:
                for idx, bar in enumerate(prof.bars, 1):
                    writer.writerow(_bar_row(bar, idx, cfg))
            else:
                writer.writerow([labels.no_stock] + pad(1))

            writer.writerow(pad(0))

        # ── Purchase aggregation (feedback #10) ───────────────
        agg: dict[tuple[str, str, float], int] = {}
        for prof in result.profiles:
            for bar in prof.bars:
                key = (
                    prof.profile,
                    prof.material or bar.material,
                    float(bar.original_length),
                )
                agg[key] = agg.get(key, 0) + 1

        if agg:
            writer.writerow([labels.purchase_sheet] + pad(1))
            purchase_headers = [
                labels.profile,
                labels.material,
                labels.bar_length,
                labels.bars_used,
                labels.linear_meters,
            ]
            writer.writerow(purchase_headers + pad(len(purchase_headers)))

            sorted_keys = sorted(agg.keys(), key=lambda k: (k[0], k[1], -k[2]))
            last_group: tuple[str, str] | None = None
            group_total_m = 0.0
            grand_total_m = 0.0

            def _subtotal(profile: str, material: str, total_m: float):
                label = profile + (f" / {material}" if material else "")
                writer.writerow(
                    [
                        f"{labels.total} {label}",
                        "",
                        "",
                        "",
                        f"{total_m:.2f}",
                    ]
                    + pad(5)
                )

            for key in sorted_keys:
                profile, material, length = key
                count = agg[key]
                linear_m = (length * count) / 1000.0

                if last_group is not None and (profile, material) != last_group:
                    _subtotal(last_group[0], last_group[1], group_total_m)
                    group_total_m = 0.0

                writer.writerow(
                    [
                        profile,
                        material,
                        int(length),
                        count,
                        f"{linear_m:.2f}",
                    ]
                    + pad(5)
                )
                group_total_m += linear_m
                grand_total_m += linear_m
                last_group = (profile, material)

            if last_group is not None:
                _subtotal(last_group[0], last_group[1], group_total_m)

            writer.writerow(
                [
                    labels.total,
                    "",
                    "",
                    "",
                    f"{grand_total_m:.2f}",
                ]
                + pad(5)
            )

    return out

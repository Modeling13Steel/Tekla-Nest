#!/usr/bin/env python3
"""Quick demo: run the nest optimizer from the command line.

Usage:
    # With a parts CSV:
    uv run python -m tekla_nest.demo parts.csv

    # With built-in sample data:
    uv run python -m tekla_nest.demo
"""

from __future__ import annotations

import sys
from pathlib import Path

from tekla_common.config.app_config import load_config

from tekla_nest.models import CutPiece, PartEntry, StockBar
from tekla_nest.services.csv_loader import load_parts_csv
from tekla_nest.services.nest_engine import NestEngine
from tekla_nest.services.pdf_report import render_report_html
from tekla_nest.services.stock_rules import generate_default_stock


def _sample_parts() -> list[PartEntry]:
    """Built-in sample data for quick testing."""
    return [
        PartEntry(quantity=4, length=3500, reference="C1", profile="HEA240", material="S275JR"),
        PartEntry(quantity=2, length=5200, reference="C2", profile="HEA240", material="S275JR"),
        PartEntry(quantity=6, length=2800, reference="C3", profile="IPE200", material="S355"),
        PartEntry(quantity=3, length=4100, reference="C4", profile="IPE200", material="S355"),
    ]


def main() -> None:
    cfg = load_config()

    # Load parts from CSV or use sample data
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        print(f"Loading parts from: {csv_path}")
        parts = load_parts_csv(csv_path)
    else:
        print("Using built-in sample data (pass a CSV path as argument to use your own)")
        parts = _sample_parts()

    # Show parts
    print(f"\n{'=' * 60}")
    print("  Parts to cut")
    print(f"{'=' * 60}")
    print(f"  {'Qty':>4}  {'Length':>8}  {'Ref':<8}  {'Profile':<12}  {'Material'}")
    print(f"  {'-' * 4}  {'-' * 8}  {'-' * 8}  {'-' * 12}  {'-' * 10}")
    for p in parts:
        print(
            f"  {p.quantity:>4}  {p.length:>8.0f}  {p.reference:<8}  {p.profile:<12}  {p.material}"
        )

    # Get distinct profiles and generate market stock
    profiles = sorted(set(p.profile for p in parts))
    stock_entries = generate_default_stock(profiles)

    print(f"\n{'=' * 60}")
    print(f"  Auto-generated stock ({len(stock_entries)} entries)")
    print(f"{'=' * 60}")

    # Run optimization per profile
    engine = NestEngine(
        kerf_width=cfg.kerf_width,
        scrap_threshold=cfg.scrap_threshold,
        max_strategies=cfg.max_strategies,
    )

    all_profile_results = []

    for profile in profiles:
        # Expand parts into individual CutPieces
        profile_parts = [p for p in parts if p.profile == profile]
        pieces: list[CutPiece] = []
        for p in profile_parts:
            for _ in range(p.quantity):
                pieces.append(CutPiece(length=p.length, mark=p.reference))

        # Expand stock into individual StockBars
        profile_stock = [s for s in stock_entries if s.profile == profile]
        bars: list[StockBar] = []
        for s in profile_stock:
            for _ in range(s.quantity):
                bars.append(
                    StockBar(
                        length=s.length,
                        mark=s.profile,
                        material=s.material or profile_parts[0].material,
                        source=s.source,
                    )
                )

        result = engine.optimize(pieces, bars)
        if result is None:
            print(f"\n  [{profile}] No feasible solution!")
            continue

        all_profile_results.append(result)

        print(
            f"\n  [{profile}]  Bars used: {len(result.bars)}"
            f"  |  Waste: {result.waste_pct:.1f}%"
            f"  |  Scrap: {result.scrap_pct:.1f}%"
        )

        for i, bar in enumerate(result.bars, 1):
            cuts_str = " + ".join(f"{c:.0f}" for c in bar.cuts)
            marks_str = ", ".join(bar.cut_marks) if bar.cut_marks else ""
            print(
                f"    Bar {i}: {bar.original_length:.0f}mm"
                f"  →  [{cuts_str}]"
                f"  free={bar.free_length:.0f}mm"
                f"  ({marks_str})"
            )

    # Generate HTML report
    if all_profile_results:
        from tekla_nest.models import NestResult, ProfileResult

        nest_result = NestResult(
            profiles=[
                ProfileResult(
                    profile=profiles[i], bars=r.bars, waste_pct=r.waste_pct, scrap_pct=r.scrap_pct
                )
                for i, r in enumerate(all_profile_results)
            ]
        )

        report_path = Path("demo_report.html")
        render_report_html(nest_result, output_path=report_path)

        print(f"\n{'=' * 60}")
        print(f"  Overall waste: {nest_result.overall_waste_pct:.1f}%")
        print(f"  Report saved:  {report_path.resolve()}")
        print(f"{'=' * 60}")
        print(f"\n  Open in browser:  open {report_path}")


if __name__ == "__main__":
    main()

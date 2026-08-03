# M5 · Report polish (HTML + chips + insights)

**Branch**: `feat/ui-m5-report` (off `feat/ui-m4-palette`)
**Status**: 🟢 Done

## What this milestone does

Brings the report surface up to the v2.1 mock spec:

* **5a** — `resources/report_template.html` modernised with a 4-card
  bento KPI hero (overall waste · total bars · unfit count · profile
  count), an inline SVG cut-bar visualisation per bar, and an amber
  bordered card for unfit pieces.
* **5b** — `ReportPreviewWidget` now composes three regions:
  `ReportFilterBar` (profile chips, exclusive selection, "All"
  default) on top, the existing `QTextBrowser` in the centre, and a
  new `InsightSidebar` on the right.
* **5c** — `services/insights.py` heuristics engine (3 rules: add
  stock for unfit pieces, high-waste warning, mixed-materials
  warning) surfaces actionable cards in the sidebar.

Filter chip changes and insight action buttons travel back to the
presenter via a single `ReportPreviewWidget.action_requested(str,
dict)` signal. The presenter owns re-rendering and stock requests so
the widget never imports the engine.

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/services/insights.py` | Pure heuristics engine. 3 rules, no Qt. `Insight` frozen dataclass with tuple-context. |
| `src/tekla_nest/views/widgets/insight_sidebar.py` | Right-rail QWidget. Renders one card per insight with optional action button. |
| `src/tekla_nest/views/widgets/report_filter_bar.py` | Exclusive QButtonGroup of profile chips + "All". |
| `src/tekla_nest/views/report_preview.py` | Rewritten to compose filter bar + browser + sidebar. Legacy API preserved. |
| `src/tekla_nest/presenters/nest_presenter.py` | New slots: `report_filter_changed(profile)` and `request_stock(profile, length, piece_count)`. |
| `src/tekla_nest/views/nest_window.py` | New dispatcher `_on_report_action`. |
| `resources/report_template.html` | Bento KPI hero, SVG cut-bar viz, amber unfit card. |
| `resources/languages/{en,pt}.yaml` | New keys under `insights.*` and `report.filter.*` (EN/PT parity). |
| `tests/unit/test_insight_engine.py` | 8 tests — empty, add_stock, high_waste threshold, mixed_materials, ordering. |
| `tests/unit/test_insight_sidebar.py` | 4 pytest-qt tests — empty, action emit, no-action, rebuild. |
| `tests/unit/test_report_filter.py` | 4 pytest-qt tests — default, populate, signal, rebuild. |
| `tests/unit/test_report_html_unfit.py` | 2 tests — KPI hero/SVG/amber card present; absent when no unfit. |

## Decisions explained

* **Heuristics are pure functions** — `services/insights.py` only
  depends on `models/`. No QApplication is required to test rules,
  which keeps the engine independently certifiable.
* **`Insight.context` is a tuple-of-tuples** so the frozen dataclass
  stays hashable. `context_dict()` converts on demand for emission.
* **The widget never imports the engine for re-rendering.** When the
  user clicks a chip, the widget emits
  `action_requested("report_filter_changed", {"profile": name})` and
  the presenter does the Jinja2 re-render with the narrowed result.
  This keeps the engine ↔ view boundary clean (§10.6).
* **`request_stock` is presenter-side** — the sidebar passes the full
  insight context (`profile`, `length`, `piece_count`) to a single
  presenter slot. Wiring a stock-dialog is out-of-scope for M5; for
  now the slot emits an info-level `error_occurred` so the status bar
  surfaces the suggestion.
* **HTML hero uses CSS `display: table`** instead of flexbox or
  grid — Qt's `QTextBrowser` Jinja renderer (used in the embedded
  preview) doesn't support modern layouts. Tables render identically
  in `QTextBrowser` and in Qt's print pipeline.
* **SVG bar viz uses fixed `width="600"`** — the report is generated
  for A4 portrait; 600 pixels at the default 96 DPI lands inside the
  print margin and scales gracefully in `QTextBrowser`.

## Validation gate

| Gate | Result |
| --- | --- |
| `pytest -q` | **355 passed** (was 334 in M4; +21 new) |
| `ruff check src tests` | **All checks passed!** |
| `scripts/check_loc.py` | **LOC budgets OK** (`report_preview.py` ≈ 184 LOC, budget 400) |
| Coverage (new modules) | insights 100% · insight_sidebar 98% · report_filter_bar 91% (gate ≥ 85%) |
| i18n EN/PT parity | preserved (new keys added to both) |

## Notes for reviewers

* The `unfit-card` and `kpi-warning` CSS classes are intentionally
  applied as `class="unfit-card"` (not just declared in `<style>`)
  so the regression test can distinguish "card present" from "CSS
  declared". See `test_report_html_unfit.py`.
* The insight ordering is stable: `add_stock` (warning) first,
  `high_waste` (warning) second, `mixed_materials` (info) last. The
  engine returns insights in this order and the sidebar preserves
  the iteration order.
* The amber palette (`#E0A23A`, `#FFF7E0`, `#B36A00`) is held inline
  in the template (not pulled from `tokens`) because the report
  surfaces in both light and dark Qt themes — the warning hue must
  read identically in both.

## What unblocks next

M6 (Tables polish + filter chips) can reuse the chip styling
introduced here. The presenter's `report_filter_changed` pattern
is also the template for M6's table-filter wiring.

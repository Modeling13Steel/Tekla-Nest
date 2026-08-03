# M3 · KPI binding + presenter signal

**Branch**: `feat/ui-m3-kpi-binding` (off `feat/ui-m2-chrome`)
**Status**: 🟢 Done

## What this milestone does

Wires the four KPI cards introduced in M2 (`KpiStrip`) to real optimisation
data emitted by `NestPresenter`. The view layer never imports engine types;
all data flows through the new `OptimizationSummary` view-model so the
strip can be reused (admin window, future dashboards) without recompiling
against the engine internals.

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/models/optimization_summary.py` | Frozen view-model derived from `NestResult`; pure data, zero Qt. |
| `src/tekla_nest/presenters/nest_presenter.py` | Adds `optimization_summary_changed = Signal(object)` and emits it from `run_optimization`, the async finish slot, and `clear_parts` (None). |
| `src/tekla_nest/views/widgets/kpi_strip.py` | `set_summary` now toggles a `state="warning"` Qt dynamic property on the *unfit* card whenever `unfit_count > 0`. |
| `src/tekla_nest/views/nest_window.py` | One-line wiring: `presenter.optimization_summary_changed → kpi_strip.set_summary`. |
| `tests/unit/test_optimization_summary.py` | 6 cases covering empty, full-fit, unfit aggregation, multi-profile, and frozen-dataclass. |
| `tests/unit/test_presenter_summary_signal.py` | Asserts `clear_parts` emits `None` and `run_optimization` emits exactly one `OptimizationSummary`. |
| `tests/unit/test_kpi_strip_binding.py` | Renders summary values, toggles warning state, and resets on `None`. |

## Decisions explained

* **Signal payload type = `object`** — Qt signals don't natively type
  dataclasses; `object` keeps the API future-proof and tested at the Python
  layer via assertions on instance type.
* **`from_nest_result(None)` returns `None`** — keeps the `clear_parts`
  path symmetrical: presenter emits `None`, strip resets to placeholders.
  Avoids an extra "is initialised?" flag in the view.
* **Warning toggle lives in `KpiStrip.set_summary`**, not in QSS via a
  `[state="warning"]` selector on the whole strip — keeps the visual
  contract local to the unfit card. Themes can extend with QSS targeting
  `QFrame[role="kpi-card"][state="warning"]`.
* **No motion yet** — count-up animation is deferred to M8 per the ROADMAP
  motion guidance; the `prefer_reduced_motion` preference doesn't yet have
  a UI surface.

## Validation gate

```
.venv/bin/python -m pytest -q                              # 313 passed
.venv/bin/python -m ruff check src tests                   # clean
.venv/bin/python scripts/check_loc.py                      # LOC budgets OK
.venv/bin/python -m pytest --cov=tekla_nest.models.optimization_summary
  --cov=tekla_nest.views.widgets.kpi_strip ...             # 100% / 95%
```

## Notes for reviewers

* `OptimizationSummary` lives under `models/` (not `presenters/`) because
  it's a pure value object shared between the presenter and any future
  read-only consumers (admin window, REST exporters, headless smoke tests).
* The async finish slot was already calling `result_ready.emit`; we added
  the summary emission immediately after so the two signals stay paired.
  Any future call site that emits `result_ready` must also emit the
  summary — a regression test on the async path can be added in M7/M8
  when the async pipeline gets revisited.
* `KpiStrip._cards[2]` is the unfit card by index. The card order is
  declared by `_CARDS` at module top; if the order changes the test will
  pinpoint the regression.

## What unblocks next

M4 (command palette) can now reuse `OptimizationSummary` to colour the
palette's "Recent results" hint card when a previous run produced unfit
pieces. M7 will bind `ThemeService.themeChanged` to the strip's QSS
refresh so the warning colour swaps with the active theme.

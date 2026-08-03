# M2 — Chrome split, KPI strip, ambient status bar

> **Status:** 🟢 Done · **Branch:** `feat/ui-m2-chrome` (branched off `feat/ui-m1-tokens`)
> **Mock reference:** `docs/ui-mocks/01-main-shell.html` (top chrome region) · `docs/ui-mocks/styles.css` selectors `.app-chrome`, `.theme-toggle`, `.kpi-strip`, `.status-bar`.

## What this milestone does

M2 decomposes the legacy ``BrandedToolbar`` + ad-hoc menu+toolbar builder in
``NestWindow`` into focused widgets and helpers. The visible shape of the
running app is the same, but the structural cost of changing it is now
dramatically lower:

- ``views/widgets/app_chrome.py`` — top bar with logo · title · quick-action
  group · command-palette trigger (disabled until M4) · theme toggle (cycles
  Light → Dark → System) · language combo. Exposes ``add_action()`` so the
  high-frequency menu items the user requested (load Tekla, load CSV, clear
  parts, auto stock, calculate, export PDF) stay one click away.
- ``views/widgets/kpi_strip.py`` — 4-card summary band ready for M3 binding.
  Cards render dashes until ``set_summary()`` is called with an
  ``OptimizationSummary``-like object.
- ``views/widgets/status_bar.py`` — ``AmbientStatusBar`` (a ``QStatusBar``)
  with status text + a traffic-light dot whose colour is QSS-driven.
- ``views/nest_menu.py`` — ``MenuBuilder`` extracted from ``NestWindow``.
  Same menu shape, but builds it from declarative ``_Cmd`` tuples so M4 can
  feed the command palette from the same source of truth.
- ``views/nest_dialogs.py`` — ``QFileDialog`` wrappers extracted from
  ``NestWindow`` slots so the window's slots reduce to one-liners.

## Artefacts

| Path | LOC | Coverage | Role |
| --- | --- | --- | --- |
| `views/widgets/app_chrome.py` | 160 | 98% | Top bar widget |
| `views/widgets/kpi_strip.py` | 111 | 97% | KPI cards strip |
| `views/widgets/status_bar.py` | 65 | 100% | Bottom status bar |
| `views/nest_menu.py` | 151 | 100% | Menu builder |
| `views/nest_dialogs.py` | 92 | 100% | File-dialog helpers |
| `views/nest_window.py` | **253** | 88% | Slim shell (was 446) |
| `resources/languages/{en,pt}.yaml` | +28 keys each | — | Chrome + KPI + status copy |
| `tests/unit/test_app_chrome.py` | 7 tests | — | Theme cycle, language combo, palette stub |
| `tests/unit/test_kpi_strip.py` | 5 tests | — | Cards + placeholder behaviour |
| `tests/unit/test_status_bar.py` | 4 tests | — | Level transitions + invalid input |
| `tests/unit/test_i18n_load.py` | 12 tests | — | EN/PT parity + M2 keys present |
| `tests/unit/test_nest_dialogs.py` | 8 tests | — | QFileDialog mocked smoke tests |

## Decisions explained

- **Quick-access actions stay in the chrome.** The bare-bones M2 mockup shows
  only palette + theme + language in the top bar, but the user previously
  asked for shortcut buttons on the top-right for load-parts / clear-parts.
  ``AppChrome.add_action()`` honours that requirement. ``test_window_toolbar_exposes_high_frequency_actions``
  has been updated to introspect ``window._chrome.actions()`` instead of the
  removed ``window._toolbar``.
- **``StatusBanner`` not yet deprecated.** The legacy ``StatusBanner`` widget
  is still re-exported from ``design_system`` because the admin window still
  uses it. Marking it deprecated lands in M5/M6 once the report panel is
  rewritten.
- **``KpiStrip`` accepts a duck-typed summary.** Using a ``Protocol`` instead
  of importing a concrete dataclass means M3 can define
  ``OptimizationSummary`` without M2 needing to ship a stub model. Missing
  fields fall back to the placeholder.
- **Menu construction is declarative.** ``_Cmd`` tuples + ``_resolve_slot``
  let the same data drive both the menu and (in M4) the command palette
  index. No more hand-written ``self._add_action(...)`` repetition.
- **File dialogs return path strings, never tuples.** ``nest_dialogs``
  callers get a clean ``if path:`` test path; the empty-string return
  pattern keeps cancellation handling trivial.
- **EN/PT parity is now a test.** Closes risk R-06 from
  ``REFACTOR_PLAN.md``. Future milestones cannot ship a translation drift
  without breaking ``test_i18n_load.py``.

## Validation gate

| Check | Result |
| --- | --- |
| `pytest -q` | **300 passed** (+41 vs M1) |
| `ruff check src tests` | **All checks passed** |
| `scripts/check_loc.py` | **LOC budgets OK** |
| `nest_window.py` LOC | **253** (target ≤ 320, was 446 in M0) |
| Coverage on new widgets | 97–100% (gate ≥ 85%) |
| EN/PT key parity | enforced by `test_i18n_load.py` |

## Notes for reviewers

- ``BrandedToolbar`` survives only because the admin window still imports it.
  It is no longer used by the main shell.
- ``AppChrome.theme_toggled`` signal is **not wired** to ``ThemeService`` in
  M2. Wiring lands in M7 along with the View → Theme menu and bootstrap
  changes in ``main.py``.
- ``KpiStrip.set_summary`` accepts any duck-typed object; M3 will define the
  real ``OptimizationSummary`` dataclass and pass it via the presenter.
- The palette trigger button is intentionally disabled. M4 enables it and
  hooks ``Ctrl+K``.

## What unblocks next

- **M3** can define ``OptimizationSummary`` and connect
  ``NestPresenter.result_ready`` to ``KpiStrip.set_summary``.
- **M4** can index the menu via the same ``_Cmd`` table that ``MenuBuilder``
  uses and bind ``Ctrl+K`` to the palette trigger.
- **M7** can call ``self._chrome.theme_toggled.connect(theme_service.apply)``
  and ``theme_service.themeChanged.connect(...setStyleSheet)`` in
  ``NestWindow`` or ``main.py``.

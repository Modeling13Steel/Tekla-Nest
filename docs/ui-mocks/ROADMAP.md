# Tekla Nest UI Refactor — Roadmap (v2.0 → v2.1)

> Authoritative execution plan for the UI refactor. Companion to:
> - `docs/ui-mocks/index.html` — visual brief
> - `docs/ui-mocks/REFACTOR_PLAN.md` — design research + decisions
>
> **Status**: Decisions locked 2026-05-22. Ready to start M1.
> **Owner**: UI working group.
> **Target release**: v2.1.0.
> **Timebox**: 10–12 engineering days across 9 milestones.

---

## 0 · How to use this document

- **Each milestone is a single PR.** Don't bundle milestones. Easier review, easier rollback.
- **DoD = Definition of Done.** A milestone is done **only** when every DoD checkbox is true.
- **VAL = Validation Gate.** Concrete commands that must pass before merge.
- **MOCK = Mockup reference.** Filename + visual element being implemented.
- **Progress tracker**: §9. Update the table in the same PR.
- **Coding guidelines**: §10 are non-negotiable. PR review checklist mirrors them.

---

## 1 · Locked decisions (recap)

| # | Decision | Source |
|---|---|---|
| Q1 | Top chrome only, no left rail | `REFACTOR_PLAN.md` §8 |
| Q2 | Mockup palette (brand unchanged, new neutrals + dark scale) | `REFACTOR_PLAN.md` §8 |
| Q3 | Static heuristic insights (no LLM) | `REFACTOR_PLAN.md` §8 |
| Q4 | Command palette scope = commands only | `REFACTOR_PLAN.md` §8 |
| Q5 | Reduced motion = preference, default OFF | `REFACTOR_PLAN.md` §8 |
| Q6 | Status bar = status text only | `REFACTOR_PLAN.md` §8 |

---

## 2 · Pre-flight (M0) — Baseline (½ day)

**Goal**: Lock the floor we can't regress below.

### Tasks
- [ ] Capture screenshots: `python -m tekla_nest` on Windows, EN + PT, 100/125/150% DPI, light only.
  - Store under `docs/ui-mocks/baseline/{en|pt}/{100|125|150}-{screen}.png`.
- [ ] Snapshot test counts: `.venv/bin/python -m pytest -q | tee docs/ui-mocks/baseline/test-floor.txt` → expect **240 passed**.
- [ ] Snapshot LOC budget per file (see §10.3) into `docs/ui-mocks/baseline/loc.txt`.
- [ ] Add dev dependencies (Phase-1 tooling): `ruff`, `pytest-cov`. Update `[project.optional-dependencies].dev`.
- [ ] Add `[tool.ruff]` + `[tool.coverage.run]` blocks to `pyproject.toml` (config in §10.6).

### DoD
- [ ] All baseline artefacts committed.
- [ ] `ruff check` runs clean on `src/` (initial config tolerant; tightened in M9).
- [ ] `pytest --cov=tekla_nest --cov-report=term-missing` produces baseline coverage report.

### VAL
```
.venv/bin/python -m pytest -q                              # 240 passed
.venv/bin/python -m ruff check src tests                   # 0 errors
.venv/bin/python -m pytest --cov=tekla_nest -q             # baseline coverage logged
```

### MOCK
N/A — no visual change.

---

## 3 · Milestones

### M1 · Token + ThemeService foundation (1.5 days) — `feat/ui-m1-tokens`

**Goal**: Land the new token vocabulary and a `ThemeService` capable of runtime light/dark swap. **No visual change in light mode.**

#### Implementation
1. Extend `src/tekla_nest/design_system/tokens.py`:
   - Add neutral fields: `text_secondary`, `border_soft`, `border_strong`, `bg_app_2`, `bg_surface_2`, `bg_elevated`.
   - Add rgba fields: `bg_glass`, `bg_overlay`, `shadow_low`, `shadow_medium`, `shadow_high`.
   - Add new radii: `radius_card: int = 12`, `radius_pill: int = 999`, `radius_field: int = 8`. Keep `control: int = 6`.
   - Add `motion_fast: int = 120`, `motion_base: int = 200` (ms).
   - Add `Theme(Enum) = {SYSTEM, LIGHT, DARK}`.
   - Add `DarkColorTokens` dataclass mirroring `ColorTokens`. Values come from `docs/ui-mocks/styles.css` `[data-theme="dark"]` block.
2. New `src/tekla_nest/services/theme_service.py`:
   - `class ThemeService(QObject)` with signal `themeChanged(Theme)`.
   - `apply(theme: Theme)` swaps a **pre-built** stylesheet (built once at startup).
   - `current() -> Theme`.
   - Persists choice to `~/.tekla_nest/preferences.json` under key `"theme"`.
   - On startup with `Theme.SYSTEM`, reads `QGuiApplication.styleHints().colorScheme()` (Qt ≥ 6.5).
3. Refactor `src/tekla_nest/theme.py`:
   - `build_app_stylesheet(cfg, theme: Theme)` — now takes a theme.
   - Add `build_all_stylesheets(cfg) -> dict[Theme, str]` returning the pre-built map.
4. `src/tekla_nest/main.py` constructs `ThemeService` and calls `apply()` before `NestWindow.show()`.

#### Tests (new)
- `tests/unit/test_design_tokens_dark.py` — hex validity, AA contrast (text vs bg_surface, bg_app) using existing `accessibility.py` helpers.
- `tests/unit/test_theme_service.py` — `apply()` emits signal, persistence round-trip, SYSTEM resolves to LIGHT or DARK.
- `tests/unit/test_theme_build.py` — both sheets contain expected selectors (`QMainWindow`, `QPushButton`, `#appShell`, `#brandToolbar`).

#### DoD
- [ ] `theme_service.py` exists and is wired in `main.py`.
- [ ] Existing `theme.py` consumers compile (back-compat: light-theme output is byte-identical or visually identical to v2.0).
- [ ] `nest_window.py` LOC unchanged ±5.
- [ ] Tests added; total ≥ 248 passing.
- [ ] Coverage on `services/theme_service.py` and `design_system/tokens.py` ≥ 90%.

#### VAL
```
.venv/bin/python -m pytest -q                                          # ≥ 248
.venv/bin/python -m pytest --cov=tekla_nest -q                         # no per-file regression
.venv/bin/python -m ruff check src tests
```
Manual: open the app, switch theme via `ThemeService.apply(Theme.DARK)` in a Python shell — dark mode renders, no crash, no console warnings.

#### MOCK
Reference: `docs/ui-mocks/styles.css` `:root` + `[data-theme="dark"]` blocks. No screen rendered yet.

---

### M2 · Chrome split (1 day) — `feat/ui-m2-chrome`

**Goal**: Decompose `BrandedToolbar` + ad-hoc toolbar building into three small widgets. **Visual delta**: same look, structurally cleaner; KPI slots empty.

#### Implementation
1. New `src/tekla_nest/views/widgets/app_chrome.py`:
   - `AppChrome(QWidget)` — top bar: logo (left) · title · spacer · **command palette trigger** (placeholder button, disabled until M4) · theme toggle (`QToolButton` cycling Light → Dark → System) · language combo.
   - Height: 56px (matches current).
   - Exposes `set_status(text)` no-op (status moves to bottom in M2.b below).
2. New `src/tekla_nest/views/widgets/kpi_strip.py`:
   - `KpiStrip(QWidget)` — 4 `KpiCard` slots. Each card: label · value · trend hint.
   - Public API: `set_summary(summary: OptimizationSummary | None)`. Summary type stubbed for M3.
   - When summary is `None` → cards render placeholder dashes.
3. New `src/tekla_nest/views/widgets/status_bar.py`:
   - `AmbientStatusBar(QStatusBar)` with status text + traffic-light dot (green/amber/red via QSS dynamic property `state`).
   - `StatusBanner` becomes a 3-line shim that forwards to the new widget to avoid churning tests. Mark with `# DEPRECATED — removed in v2.2`.
4. `nest_window.py`:
   - Replace `BrandedToolbar` + manual toolbar with `AppChrome`.
   - Add `KpiStrip` immediately below `AppChrome`.
   - Replace `StatusBanner` with `AmbientStatusBar` (via `setStatusBar`).
   - Target LOC: **≤ 320** (was 446).

#### i18n keys (EN + PT, both updated in same commit)
- `chrome.theme_toggle.tooltip`
- `chrome.theme_toggle.light` / `.dark` / `.system`
- `chrome.command_palette.tooltip`
- `kpi.waste_pct` / `.bars_used` / `.unfit_count` / `.profile_count`
- `kpi.placeholder` (e.g. `"—"`)
- `statusbar.state.idle` / `.busy` / `.error`

#### Tests
- `tests/unit/test_app_chrome.py` — contains expected child widgets, theme toggle cycles through 3 states, exposes all `CommandDescriptor` actions in tooltips.
- `tests/unit/test_kpi_strip.py` — renders 4 cards, placeholder when summary is None.
- `tests/unit/test_status_bar.py` — `state` property drives dot colour class.
- Extend `tests/unit/test_i18n_load.py` to assert EN and PT key sets are identical (closes risk R-06 from `REFACTOR_PLAN.md`).

#### DoD
- [ ] `nest_window.py` ≤ 320 LOC.
- [ ] No regressions in `test_nest_window.py` (or equivalent integration tests).
- [ ] Theme toggle visually swaps light → dark when clicked.
- [ ] All new strings present in `en.yaml` and `pt.yaml`.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 260
.venv/bin/python -m pytest tests/unit/test_i18n_load.py -q          # EN/PT parity
wc -l src/tekla_nest/views/nest_window.py                           # ≤ 320
```

#### MOCK
- `docs/ui-mocks/01-main-shell.html` lines 1–60 (top chrome region).
- `docs/ui-mocks/styles.css` `.app-chrome`, `.theme-toggle`, `.kpi-strip`, `.status-bar`.

---

### M3 · KPI binding + presenter signal (1 day) — `feat/ui-m3-kpi-binding`

**Goal**: Wire real optimisation data into the KPI strip.

#### Implementation
1. New `src/tekla_nest/models/optimization_summary.py`:
   ```python
   @dataclass(frozen=True)
   class OptimizationSummary:
       waste_pct: float
       bars_used: int
       unfit_count: int
       profile_count: int
   ```
   Pure view-model — derived from `NestResult`. Lives in `models/` so views never import engine types directly.
2. `NestPresenter`:
   - New Qt signal `optimization_summary_changed = Signal(object)` (`object` because we ship a frozen dataclass).
   - Emit `OptimizationSummary.from_nest_result(result)` at the end of `run_nest`.
   - Emit `None` from `clear_parts` and on init.
3. `KpiStrip` subscribes to the signal in `NestWindow.__init__`.
4. Add count-up animation **only** if `prefer_reduced_motion` is `False` (preference defaults to `False`; the toggle UI ships in M8).

#### Tests
- `tests/unit/test_optimization_summary.py` — `from_nest_result` correctness on fixtures (full fit, partial fit with unfit pieces, empty result).
- `tests/unit/test_presenter_summary_signal.py` — `run_nest` emits one summary; `clear_parts` emits `None`.
- `tests/unit/test_kpi_strip_binding.py` — signal updates card values; `None` → placeholders.

#### DoD
- [ ] After a `run_nest`, all 4 KPIs reflect the result.
- [ ] After `clear_parts`, KPIs reset to placeholders.
- [ ] `unfit_count > 0` styles the unfit card with `state=warning` (QSS dynamic property).

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 268
```
Manual: run a nest with a known fixture (5 × 6100mm parts, 2 × 6100mm bars) → unfit_count = 3, card glows amber.

#### MOCK
- `docs/ui-mocks/01-main-shell.html` lines 60–110 (KPI strip).
- `docs/ui-mocks/styles.css` `.kpi-card`, `.kpi-card[data-state="warning"]`.

---

### M4 · Command Palette (Ctrl+K) (2 days) — `feat/ui-m4-palette`

**Goal**: Ship Ctrl+K palette listing every registered command. Scope locked to commands only (Q4).

#### Implementation
1. New `src/tekla_nest/views/command_palette.py`:
   - `class CommandPalette(QDialog)` — frameless, translucent backdrop via `Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog`.
   - Widgets: `QLineEdit` (search) + `QListView` + model.
   - Model: pulls from `design_system/commands.py` registry.
   - Filtering: sub-sequence fuzzy match (in-process, no `rapidfuzz` dep). See §10.7 reference implementation.
   - Invocation: `QAction.trigger()` — same path as menu/toolbar so license gates and disabled state automatically apply.
2. `NestWindow.__init__`:
   - Bind `QShortcut(QKeySequence("Ctrl+K"), self, self._open_palette)`.
   - Wire `AppChrome` palette trigger to the same slot.
3. Recency + frequency:
   - On invoke, append `(command_id, timestamp)` to `~/.tekla_nest/preferences.json["palette_history"]` (cap 100).
   - Ranking: matches first, then recency-decayed frequency. Pure function in `services/palette_ranker.py`.

#### i18n keys (EN + PT)
- `palette.placeholder` — `"Search for a command…"` / `"Procurar um comando…"`
- `palette.no_results`
- `palette.recent`
- `palette.category.file` / `.edit` / `.view` / `.help` (mirrors existing menu structure)

#### Accessibility
- `QAccessible.Role.ListItem` on each result row.
- Up/Down/Home/End navigate; Enter triggers; Esc closes.
- Selected item announced via `QAccessible.updateAccessibility`.
- Focus ring uses `tokens.focus_ring`.

#### Tests
- `tests/unit/test_palette_ranker.py` — sub-sequence match, recency wins on ties, capped at 100 history items.
- `tests/unit/test_command_palette.py` (pytest-qt):
  - Opens on Ctrl+K.
  - Filters as user types.
  - Enter triggers the underlying `QAction`.
  - Disabled commands rendered greyed and not invokable.
  - License-gated commands hidden when license absent.
  - Both EN and PT labels are matchable.

#### DoD
- [ ] Ctrl+K opens palette over the main window.
- [ ] All `CommandDescriptor` entries listed.
- [ ] Selection triggers identical behaviour to menu click.
- [ ] No new external deps in `pyproject.toml`.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 280
.venv/bin/python -m pytest tests/unit/test_command_palette.py -q
```

#### MOCK
- `docs/ui-mocks/03-command-palette.html` (entire file).
- `docs/ui-mocks/styles.css` `.palette`, `.palette-results`, `.palette-row[aria-selected]`.

---

### M5 · Report polish (2.5 days) — `feat/ui-m5-report`

**Goal**: Modernise the report. HTML changes ship for free in PDF/HTML export; Qt-side composite adds interactivity.

#### Implementation
1. **5a · HTML template** (`resources/report_template.html` + the report's inline CSS):
   - Bento KPI hero (4 cards) at the top.
   - Per-profile section: inline SVG cut-bar viz (one row per bar).
   - Unfit-pieces card — surfaces `ProfileResult.unfit_pieces` (already on the model since the May 2026 engine fix). Style: amber border, lists piece IDs, suggests "add stock" action (HTML-static; Qt-side wires the action in 5c).
2. **5b · Composite Qt view** (`src/tekla_nest/views/report_preview.py`):
   - Wrap `QTextBrowser` in a `QWidget` that stacks: `KpiStrip` (reused) · filter chips row · `QTextBrowser` · `InsightSidebar`.
   - Filter chips: profile and material facets. Client-side filtering by re-rendering the Jinja template with a filtered `NestResult`.
3. **5c · `views/widgets/insight_sidebar.py`**:
   - Lists items from `ProfileResult.unfit_pieces`.
   - Lists heuristic suggestions from `services/insights.py` (new):
     ```python
     def suggest(result: NestResult) -> list[Insight]: ...
     # Heuristics in v2.1:
     #   - "Add bar of length X to fit unfit piece Y"
     #   - "Waste > 25% on profile P → consider stocking shorter bars"
     #   - "Mixed materials in same profile P → re-group to reduce setup"
     ```
   - Each insight has an action button bound to a presenter method (e.g. `presenter.request_stock_for_piece(piece_id)` — new).

#### Tests
- `tests/unit/test_report_html_unfit.py` — fixture with unfit pieces → rendered HTML contains the unfit card with piece IDs.
- `tests/unit/test_insight_engine.py` — each heuristic asserted on a tailored fixture; coverage ≥ 90% on `services/insights.py`.
- `tests/unit/test_insight_sidebar.py` (pytest-qt) — sidebar reflects current `NestResult`; clicking an action invokes the right presenter method.
- `tests/unit/test_report_filter.py` — selecting a profile chip narrows the rendered HTML to that profile.

#### DoD
- [ ] PDF export still renders correctly (manual: export with a 3-profile fixture).
- [ ] Unfit pieces visible in **both** HTML and the Qt sidebar.
- [ ] At least 3 heuristic insights implemented and tested.
- [ ] `services/insights.py` has no I/O, no network, no LLM calls.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 295
.venv/bin/python -m pytest --cov=tekla_nest.services.insights -q
```

#### MOCK
- `docs/ui-mocks/02-report-insights.html` (entire file).
- Inline cut-bar viz: lines 80–160.
- Unfit-pieces card: lines 200–240.

---

### M6 · Tables polish + filter chips (1.5 days) — `feat/ui-m6-tables`

**Goal**: Same data, modern presentation.

#### Implementation
1. New `src/tekla_nest/views/widgets/material_chip_delegate.py`:
   - `QStyledItemDelegate` painting the material column as a coloured pill.
   - Colours pulled from `tokens.material_palette` (new field; map `material_grade -> hex`).
2. Row height: 24 → 32. Padding 4 → 8 (via QSS `QTableWidget::item`).
3. Filter row above each table (new `views/widgets/table_filter_bar.py`):
   - `QLineEdit` (debounced 150ms) + material chip toggles.
   - Plugs into the existing model in `table_system.py` via `QSortFilterProxyModel` (already present).
4. Sticky header: set `setSectionResizeMode(QHeaderView.Fixed)` + use QSS `QHeaderView::section`.

#### Tests
- `tests/unit/test_material_chip_delegate.py` — paint path on a `QPixmap` snapshot.
- `tests/unit/test_table_filter_bar.py` — search narrows rows; chip toggle filters by material; debounce honoured (mock timer).
- `tests/unit/test_table_filter_integration.py` (pytest-qt) — Parts table + filter bar end-to-end.

#### DoD
- [ ] Material column rendered as chips, with AA contrast on all chip colours.
- [ ] Search + chip filtering work in Parts, Market Stock, and Client Stock tables.
- [ ] No regression in `test_stock_rules.py`, `test_presenter.py`.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 305
```

#### MOCK
- `docs/ui-mocks/01-main-shell.html` lines 110–200 (tables + filter chips).
- `docs/ui-mocks/styles.css` `.chip`, `.chip[data-active]`, `.filter-bar`.

---

### M7 · Dark mode rollout (1 day) — `feat/ui-m7-dark-mode`

**Goal**: Make dark mode user-facing.

#### Implementation
1. `Preferences → Theme` menu group (`QActionGroup`, exclusive): `System` / `Light` / `Dark`.
2. Group writes to `ThemeService.apply(theme)`.
3. Provide a dark logo variant (placeholder PNG if branding owner hasn't delivered final art).
4. Extend `design_system/brand.py:select_logo_variant` to take `Theme` directly.
5. QA pass with `accessibility.py` helpers: every `(text, bg)` pair in dark mode ≥ AA contrast.

#### Tests
- `tests/unit/test_theme_menu.py` (pytest-qt) — clicking each menu item swaps the active theme; persists across restart (mocked `preferences.json`).
- `tests/unit/test_dark_contrast.py` — every dark token pair meets WCAG AA.

#### DoD
- [ ] Theme menu exists in EN and PT.
- [ ] Restart honours the last-chosen theme.
- [ ] System mode honours OS colour scheme on Win11; falls back to LIGHT on Win10.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 315
```
Manual: switch theme three ways, restart, inspect both DPIs.

#### MOCK
- `docs/ui-mocks/04-dark-mode.html` (entire file).
- Both `:root` and `[data-theme="dark"]` blocks in `styles.css`.

---

### M8 · Motion + reduced-motion preference (½ day) — `feat/ui-m8-motion`

**Goal**: Subtle motion, with a safety switch.

#### Implementation
1. `AppConfig.prefer_reduced_motion: bool = False` (read from `config.yaml`).
2. New `src/tekla_nest/design_system/motion.py`:
   ```python
   def animate(target, prop, *, duration_ms, start, end, easing=QEasingCurve.OutCubic):
       if get_config().prefer_reduced_motion:
           target.setProperty(prop, end)
           return None
       return QPropertyAnimation(...)
   ```
3. Apply to:
   - KPI count-up (M3 placeholder gets real wiring here).
   - Palette fade-in (≤ 120ms).
   - Insight sidebar slide-in (≤ 200ms).
4. Add `Preferences → Reduced motion` toggle (writes to preferences).

#### Tests
- `tests/unit/test_motion_helper.py` — when reduced, returns `None` and sets the end value immediately.

#### DoD
- [ ] All three animations honour the preference.
- [ ] No animation exceeds 200ms.
- [ ] Toggle works at runtime without restart.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 318
```

#### MOCK
N/A — motion is timing, not visible in static mocks. Document in `docs/ui-mocks/REFACTOR_PLAN.md` §D-09.

---

### M9 · Cleanup, screenshots, release (½ day) — `chore/ui-m9-release`

**Goal**: Tighten the bolts and cut v2.1.0.

#### Tasks
- [ ] Tighten `[tool.ruff]` rules — promote warnings to errors (see §10.6).
- [ ] Re-take baseline screenshots in EN + PT, light + dark, 100/125/150% DPI. Store under `docs/ui-mocks/v2.1/`.
- [ ] Diff vs. `docs/ui-mocks/baseline/`. Reviewer signs off visually.
- [ ] Update `README.md` screenshots + feature list.
- [ ] Update `docs/specs/spec-0001/` to reference the new shell.
- [ ] Bump `pyproject.toml` version `2.0.0 → 2.1.0`.
- [ ] Tag `v2.1.0`. Generate release notes from milestone PR titles.

#### DoD
- [ ] All milestones M1–M8 merged.
- [ ] Test count ≥ 280.
- [ ] `nest_window.py` ≤ 300 LOC (final target).
- [ ] No file in `views/` > 400 LOC.
- [ ] `ruff check` clean under tightened config.
- [ ] Coverage on new files ≥ 85%.
- [ ] Release notes published.

#### VAL
```
.venv/bin/python -m pytest -q                                       # ≥ 320, all green
.venv/bin/python -m ruff check src tests                            # 0 errors
.venv/bin/python -m pytest --cov=tekla_nest --cov-report=term-missing
git tag v2.1.0
```

---

## 9 · Progress Tracker

Update this table in each milestone PR. PR title format: `M{n}: {short title}`.

| Milestone | Status | Branch | PR | Tests | LOC `nest_window.py` | Notes |
|---|---|---|---|---|---|---|
| M0 Baseline | 🟢 | `chore/ui-m0-baseline` | (local) | 240 | 446 | floor — ruff clean, cov 70 % |
| M1 Tokens + ThemeService | 🟢 | `feat/ui-m1-tokens` | M1-tokens.md | 259 | 446 | no visual change |
| M2 Chrome split | 🟢 | `feat/ui-m2-chrome` | M2-chrome.md | 300 | 253 | KPI placeholders |
| M3 KPI binding | 🟢 | `feat/ui-m3-kpi-binding` | M3-kpi-binding.md | 313 | 262 | real data |
| M4 Command palette | 🟢 | `feat/ui-m4-palette` | M4-palette.md | 334 | 274 | Ctrl+K |
| M5 Report polish | 🟢 | `feat/ui-m5-report` | M5-report.md | 355 | 286 | insights live |
| M6 Tables polish | 🟢 | `feat/ui-m6-tables` | [M6-tables.md](milestones/M6-tables.md) | 369 | 286 | chips + filter |
| M7 Dark mode | 🟢 | `feat/ui-m7-dark-mode` | [M7-dark-mode.md](milestones/M7-dark-mode.md) | 387 | 330 | menu shipped |
| M8 Motion | 🟢 | `feat/ui-m8-motion` | [M8-motion.md](milestones/M8-motion.md) | 394 | 358 | reduced-motion toggle, 200 ms cap |
| M9 Release | 🟢 | `chore/ui-m9-release` | [M9-release.md](milestones/M9-release.md) | 394 | 314 | v2.1.0 cut, ruff tightened |

Status legend: ⬜ not started · 🟡 in progress · 🟢 merged · 🔴 blocked.

---

## 10 · Strict Coding Guidelines (non-negotiable)

### 10.1 · Architecture rules
1. **Views never import from `services/` or `engine/` directly.** Views talk to `presenters/` only.
2. **Presenters never import from `views/`.** Communication is one-way via Qt signals + method calls.
3. **`models/` is pure data.** No Qt imports, no I/O.
4. **`design_system/` is pure.** No Qt widget instantiation at import time; helpers only.
5. **`services/` is framework-agnostic.** No Qt imports except in `services/theme_service.py` (which owns the QSS swap and is allowed to depend on QtGui/QtCore — not QtWidgets).

### 10.2 · Qt-specific rules
1. **Every visible string** goes through `tr()`. PR review rejects raw English strings in widget code.
2. **Every interactive widget** gets `set_accessibility(widget, name, description=None)` from `design_system/accessibility.py`.
3. **Every new `QAction`** registers a `CommandDescriptor` so the palette picks it up automatically.
4. **No inline stylesheets** on widgets (`widget.setStyleSheet(...)` is reserved for `theme.py`). Use QSS object names + dynamic properties + `force_style_refresh()`.
5. **No `QTimer` for animations** — use `QPropertyAnimation` via `design_system/motion.py`.
6. **No blocking I/O on the GUI thread.** File reads in services use the same pattern as today (synchronous but fast); anything new that's > 50ms goes on a `QThread`.
7. **No new top-level windows.** Modal interactions use `QDialog` parented to the main window.

### 10.3 · File size budgets
| Path | Max LOC | Why |
|---|---|---|
| `src/tekla_nest/views/nest_window.py` | 300 | Composition root only |
| `src/tekla_nest/views/*.py` (other) | 400 | Single-responsibility |
| `src/tekla_nest/views/widgets/*.py` | 250 | Small composable widgets |
| `src/tekla_nest/services/*.py` | 400 | Business logic, easy-to-test |
| `src/tekla_nest/design_system/*.py` | 250 | Token/utility only |
| `src/tekla_nest/theme.py` | 350 | Stylesheet builder |

Enforced by a CI check (added in M0): `scripts/check_loc.py` (10 lines, fails the build above budget).

### 10.4 · i18n rules
1. Every new string lands in **both** `en.yaml` and `pt.yaml` in the **same commit**.
2. EN/PT key-set parity is asserted by `tests/unit/test_i18n_load.py` (extended in M2).
3. Portuguese values containing colons or YAML special chars are double-quoted (see lesson from May 2026 engine fix).
4. Key naming: `category.subcategory.intent` — lowercase snake_case.

### 10.5 · Testing rules
1. **Every new module ships with tests in the same PR.** No "tests in follow-up".
2. **Coverage floor for new files: 85%.** Coverage on existing files must not drop.
3. **`pytest-qt` integration tests** for any user-visible flow (chrome interactions, palette open/select, theme toggle).
4. **No animations in tests.** Wrap timers in helpers that can be disabled.
5. **i18n tests cover both languages.** Test names: `test_..._en` and `test_..._pt` when language matters.
6. **Snapshot tests are reviewed manually** — diff a `QPixmap` to a reference PNG only when paint logic is non-trivial (M6 chip delegate qualifies).

### 10.6 · Tooling config (added in M0)

`pyproject.toml`:
```toml
[project.optional-dependencies]
dev = ["pytest>=7", "pytest-qt>=4", "pytest-cov>=5", "ruff>=0.6"]

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
# M0: lenient — catch real bugs only.
# M9: tightened to also include I (isort), B (bugbear), UP (pyupgrade).
select = ["E", "F", "W"]
ignore = ["E501"]   # line length is a soft guideline in M0; enforced from M9

[tool.coverage.run]
source = ["src/tekla_nest"]
omit = ["*/main.py", "*/admin/main.py"]

[tool.coverage.report]
skip_covered = false
show_missing = true
```

M9 promotion (tightening):
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM"]
ignore = []
```

### 10.7 · Fuzzy matcher reference (M4)
```python
def fuzzy_score(query: str, candidate: str) -> int | None:
    """Return a score (higher = better) or None if no sub-sequence match."""
    q, c = query.lower(), candidate.lower()
    if not q:
        return 0
    score, last = 0, -1
    for ch in q:
        idx = c.find(ch, last + 1)
        if idx == -1:
            return None
        # consecutive bonus
        score += 5 if idx == last + 1 else 1
        # word-start bonus
        if idx == 0 or c[idx - 1] in " /:-_":
            score += 3
        last = idx
    # shorter candidates win on ties
    return score - len(c) // 10
```
Acceptance: 100% branch coverage in `test_palette_ranker.py`.

### 10.8 · Review checklist (paste into every UI PR description)
```
- [ ] DoD checkboxes complete
- [ ] Validation gate passing locally
- [ ] No raw strings — every visible string via tr()
- [ ] Every interactive widget has set_accessibility()
- [ ] No new top-level windows; dialogs parented to main
- [ ] LOC budget respected (scripts/check_loc.py green)
- [ ] EN + PT key parity (test_i18n_load.py green)
- [ ] Tests added; coverage on new files ≥ 85%
- [ ] Mockup reference cited in PR description
- [ ] Screenshots attached (light + dark when applicable)
```

---

## 11 · Risk Reminders (carry-over from REFACTOR_PLAN.md §4)

Most-likely-to-bite during execution:
- **R-01 QSS shadows** — use `QGraphicsDropShadowEffect`, ≤ 3 per screen.
- **R-02 QTextBrowser SVG/DPI** — pre-rasterise to PNG data-URI if DPI ≠ 100%.
- **R-06 i18n key drift** — `test_i18n_load.py` enforces parity; failing this test blocks merge.
- **R-09 Dark logo missing** — ship a placeholder, file a branding ticket.

---

## 12 · Out of scope for v2.1 (deferred to v2.2)

To prevent scope creep — explicitly **not** in this roadmap:
- Real LLM insights (Q3 deferred).
- Recent files / jump-to-piece in palette (Q4 deferred).
- License-tier badge / version / telemetry in status bar (Q6 deferred).
- Left navigation rail (Q1 deferred).
- Dialog structural rework (`activation_dialog`, `color_dialog`) — token-only refresh applies automatically.
- Brand palette refresh — brand primary/accent stay on current values.

Anything in this list, if it sneaks into a PR, is a review-blocker.

---

*Last edited 2026-05-22. Update §9 in every milestone PR.*

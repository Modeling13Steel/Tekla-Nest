# UI Refactor Research — From PySide6 v2.0 to the 2026 Mockups

> Companion to the mockups in `docs/ui-mocks/`.
> Source of truth for the migration; updated as decisions land.

This document maps **what we ship today** to **what the mockups propose**, with a concrete, low-risk, phased refactor plan that respects the existing MVP architecture (`presenters/`, `services/`, `views/`, `design_system/`) and the Tekla CLR bridge.

---

## 1 · Current State (audited 2026-05-22)

### 1.1 Architecture in numbers
- `src/tekla_nest/views/` — **1,652 LOC** across 9 files. `nest_window.py` is the only fat file (446 LOC).
- `src/tekla_nest/design_system/` — **288 LOC**. Already tokenised: colors, spacing, radius, typography, status, commands, brand.
- `src/tekla_nest/theme.py` — **239 LOC**. Builds the Qt stylesheet (QSS) from tokens. Single chokepoint for visual change.
- `tests/` — 240 passing. Presenter, services, i18n, accessibility, theme-build smoke tests.

### 1.2 What works well (do not touch)
- **MVP boundary**. `NestPresenter` owns state, views are dumb. The visual refactor is *entirely* in `views/` + `design_system/` + `theme.py`. No presenter or service changes are required.
- **Token vocabulary**. Semantic tokens (`action_primary`, `state_warning`, `editable_focus_bg`…) already feed QSS. We extend, we don't replace.
- **i18n + accessibility plumbing**. `tr()`, `set_accessibility`, `apply_action_descriptor` already wrap every visible string. New widgets must use the same helpers.
- **Engine contract**. `ProfileResult.unfit_pieces` is in place. The new "insight card" UI in mock 02 just needs a Qt view binding.

### 1.3 Visual gaps vs. mockups

| Surface | Today | Mockup |
|---|---|---|
| Top chrome | `BrandedToolbar` (logo + title + actions, height 56) | Logo + title + **command palette button** + **KPI summary** + theme toggle |
| Workspace | `QSplitter` 3-panel: Parts \| Stock \| Report | Same 3-panel, but with **bento KPI strip** above, **filter chips**, **soft elevation** |
| Report | `QTextBrowser` rendering `report_template.html` | Same engine output, with **inline cut-bar SVG/QPainter visualisation** + **insight cards** + side rail of suggestions |
| Tables | `parts_table`, `stock_table` (QTableWidget-based) | Same data, modernised row spacing, colored material chips, sticky header |
| Status | `StatusBanner` single line | **Ambient status bar** at bottom (traffic-light dot, status text, license + telemetry) |
| Modals | `activation_dialog`, `color_dialog` (forms) | Same forms but in elevated cards with backdrop blur |
| Dark mode | none | `data-theme="dark"` switching via runtime token swap |
| Command palette | none | Ctrl+K overlay listing every menu/toolbar action |

### 1.4 Hard constraints the refactor must honour
- **Windows-first PySide6 6.11** desktop, no web stack.
- **No QML migration.** The team owns Widgets; QML adds build/test surface we don't need.
- **No new heavy deps.** `QtSvg` and `QtCharts` are already pulled by PySide6 — fine to use. Avoid third-party theme libs (qtawesome is acceptable for icons, qt-material is **out** — it overwrites our QSS).
- **Bilingual (EN/PT)** — every new string goes through `tr()` and `resources/languages/*.yaml`.
- **License gating** — the existing `licensing/` gate around features must wrap any new feature surface (e.g. AI insights, export-to-DSTV).
- **Backwards visual compat** — users on Windows 10 must still get a coherent UI; we can't rely on Win11 Mica.

---

## 2 · Design Decisions (proposed)

Each decision is annotated with **R**isk, **E**ffort, and **V**alue (1–5).

### D-01 · Extend tokens, don't replace them — R1 E1 V5
Add a second layer to `design_system/tokens.py` mirroring the mock CSS:
- `surface_raised`, `surface_overlay`, `surface_sunken`
- `border_subtle`, `border_strong`, `divider`
- `elevation_low/medium/high` (QSS shadow strings)
- `radius_card` (12), `radius_pill` (999), `radius_field` (8) — current `control` (6) stays for buttons
- `motion_fast` (120ms), `motion_base` (200ms) — for Qt animations
- A `Theme` enum `LIGHT | DARK` and a parallel `DarkColorTokens` dataclass

Why this first: every other change consumes tokens. Land tokens once, refactor consumers incrementally.

### D-02 · Theme service with runtime swap — R2 E2 V5
Promote `theme.py:build_app_stylesheet` to a small `ThemeService`:
- `apply(theme: Theme)` — rebuilds QSS, calls `QApplication.setStyleSheet`, emits `themeChanged`.
- Subscribed widgets refresh dynamic properties (we already have `force_style_refresh`).
- Persist choice in `~/.tekla_nest/preferences.json` (already used for license artefacts).
- Detect system preference at startup via `QGuiApplication.styleHints().colorScheme()` (Qt 6.5+, available in 6.11). Fall back to LIGHT.

### D-03 · Adopt CSS-variable-style indirection in QSS — R2 E2 V4
QSS has no real variables. We already template via Python f-strings. Tighten this by:
- Building two QSS sheets at startup (`light.qss`, `dark.qss`) into memory, switching is `setStyleSheet(self._sheets[theme])` — no rebuild on toggle.
- Adding a `--tn-` naming convention in code comments so reviewers can trace tokens → QSS rules.

### D-04 · Component-ise the chrome — R2 E3 V4
Decompose the current `BrandedToolbar` + ad-hoc `_build_toolbar_actions` into three small widgets under `views/widgets/`:
- `app_chrome.py` — `AppChrome(QWidget)`: glass-look top bar holding logo, title, command-palette trigger, theme toggle, language menu.
- `kpi_strip.py` — `KpiStrip(QWidget)`: 4 `KpiCard`s bound to presenter signals (`waste_pct`, `bars_used`, `unfit_count`, `profile_count`).
- `status_bar.py` — `AmbientStatusBar(QStatusBar)`: traffic-light icon + status text + license tier + cycle telemetry.

Each is independently testable with `pytest-qt`.

### D-05 · Command Palette (Ctrl+K) as a first-class subsystem — R2 E3 V5
- New `views/command_palette.py` — frameless `QDialog` with translucent backdrop, `QLineEdit`, `QListView`, fuzzy matcher.
- Source of truth: `design_system/commands.py:CommandDescriptor` already exists and is bound to every action. The palette just iterates the registry. **Zero duplication.**
- Action invocation goes through the **same `QAction.trigger()`** path as menus/toolbar, so license gates, enabled-state sync, and i18n already work.
- Keyboard shortcut: `Ctrl+K` global, registered on the `QMainWindow`. Esc closes. Up/Down navigates. Enter triggers.

### D-06 · Report viewport: keep HTML, add Qt-side widgets — R3 E3 V5
Two compatible strategies, applied in order:

1. **Cheap win first**: extend `resources/report_template.html` + `styles.css` to render the bento KPI hero and inline SVG cut-bars *inside* `QTextBrowser`. `QTextBrowser` supports inline SVG via `<img src='data:image/svg+xml;…'>`. Same template can be exported to PDF/HTML.

2. **Then**, where HTML hits its limits (live filtering, animated unfit-pieces card), wrap the `QTextBrowser` in a `ReportComposite` view that stacks:
   - `KpiStrip` (reused)
   - Filter chips row (profile/material facets)
   - `QTextBrowser` (the canonical report)
   - `InsightSidebar` (unfit-pieces actions + suggestions)

This keeps **print/export pixel-perfect** while modernising the on-screen experience.

### D-07 · Tables: in-place modernisation — R1 E2 V3
`parts_table.py`, `stock_table.py`, `stock_tabs.py` stay as `QTableWidget`. We:
- Increase row height (24 → 32), padding 4 → 8.
- Use `QStyledItemDelegate` to render material as a pill (`MaterialChipDelegate`).
- Add a small filter row above each table (search + material chips). Filtering is client-side over the existing model.
- Sticky header via `setSectionResizeMode(QHeaderView.Fixed)` + custom paint — already supported.

### D-08 · Dark mode is non-negotiable, but ship behind a setting — R1 E1 V4
- Add to `Preferences → Theme`: System / Light / Dark.
- Default = System.
- Auto-detect honours `QGuiApplication.styleHints().colorSchemeChanged`.
- Logo: we already have a `select_logo_variant(path, background)` helper — extend to take `Theme` directly.

### D-09 · Motion: subtle, opt-out — R2 E2 V3
- All animations through `QPropertyAnimation`, duration ≤ 200ms, easing `OutCubic`.
- Targets: command palette fade-in, KPI value count-up on optimization completion, insight card slide-in.
- Respect `QGuiApplication.styleHints().showIsFullScreen()`/reduced-motion via preference (`prefer_reduced_motion=true`) → animations disabled, transitions snap.

### D-10 · Don't rebuild the dialogs yet — R1 E0 V2
`activation_dialog.py` and `color_dialog.py` work and are tested. Visual refresh is **token-driven only** — they will pick up the new look automatically once tokens land. Defer structural rework.

---

## 3 · Refactor Phases

Each phase is a single, mergeable PR. Order is dependency-driven; each phase keeps the app green.

### Phase 0 · Capture baseline (½ day)
- Screenshot every screen at 100% / 125% / 150% DPI in EN and PT.
- Stash under `docs/ui-mocks/baseline/` (already excluded from packaging).
- Record `pytest -q` (240 passing) + coverage as the must-not-regress floor.

### Phase 1 · Token + ThemeService foundation (1–2 days) — D-01, D-02, D-03
- Extend `design_system/tokens.py` with the new fields, dark dataclass, `Theme` enum.
- Build `ThemeService` in `services/theme_service.py`. **Subscribed widgets get a `refresh_theme()` hook** that re-applies dynamic properties.
- Update `theme.py` to emit two pre-built sheets.
- New unit tests:
  - tokens hex validation for both themes,
  - QSS string contains expected selectors for both themes,
  - service emits `themeChanged` when `apply()` is called,
  - prefers system colour scheme when set to `Theme.SYSTEM`.
- No visual change yet — light theme stays pixel-identical.
- **Exit gate**: 240 → ≥ 248 tests; no screenshot diff in light mode.

### Phase 2 · Chrome split (1 day) — D-04
- Move existing toolbar items to `AppChrome`.
- Add `KpiStrip` with placeholder cards (no data binding yet).
- Add `AmbientStatusBar` replacing `StatusBanner` consumers — `StatusBanner` becomes a deprecated alias that forwards (one line) to avoid churning tests.
- `nest_window.py` shrinks: target ≤ 300 LOC.
- `pytest-qt` tests: chrome contains all action descriptors, status bar shows initial status text.

### Phase 3 · KPI binding + telemetry signals (1 day)
- `NestPresenter` exposes Qt signals: `optimization_summary_changed(summary: OptimizationSummary)` where `OptimizationSummary` is a small new dataclass in `models/`. **Pure read-model; no behaviour change.**
- `KpiStrip` consumes the signal.
- New presenter tests cover the dataclass + emission on `run_nest`.

### Phase 4 · Command Palette (2 days) — D-05
- `views/command_palette.py` + `i18n` keys (`palette.placeholder`, `palette.no_results`, …).
- Register `Ctrl+K` globally; `Escape` closes; arrow keys + Home/End navigate.
- Fuzzy match: simple sub-sequence scorer in Python (no `rapidfuzz` dep), ranks by recency + frequency stored in `preferences.json`.
- Accessibility: `QAccessible.Role.ListItem` for results, screen-reader announcement of selected command.
- Tests: 8–10 cases — open/close, filter, invoke, license-gated commands hidden when not licensed, EN/PT label matching.

### Phase 5 · Report polish (2–3 days) — D-06
- **5a** — `report_template.html` gets the bento hero + inline SVG cut-bars + unfit-pieces card. PDF export auto-improves.
- **5b** — `report_preview.py` wraps `QTextBrowser` in `ReportComposite` (vertical layout) and adds filter chips on the Qt side.
- **5c** — `InsightSidebar` consumes `ProfileResult.unfit_pieces` (already in the model) and offers "Add stock for piece X" buttons that invoke a presenter method `request_stock_for_piece(piece_id)` — to be added.
- Snapshot tests: render report HTML for a fixture nest and assert SVG/CSS presence.

### Phase 6 · Tables polish + filter chips (1–2 days) — D-07
- `MaterialChipDelegate` painting.
- Inline filter row (`QLineEdit` + chip toggles) bound to the same `QSortFilterProxyModel` strategy already used in `table_system.py`.
- Tests: filter narrows row count, chip-state preserved across re-renders.

### Phase 7 · Dark mode rollout (1 day) — D-08
- Wire `Preferences → Theme` menu group (already a pattern — see `_language_actions`).
- QA pass: confirm contrast AA in both themes via existing `accessibility.py` helpers + `Wcag` ratios in `tests/unit/test_design_tokens.py`.
- Logo variant selection extended.

### Phase 8 · Motion + reduced-motion preference (½ day) — D-09
- Add `prefer_reduced_motion` to `AppConfig` (default `False`).
- Wrap animations behind a `Motion.animate(target, prop, …)` helper that no-ops when reduced.

### Phase 9 · Cleanup, dialog token re-skin, screenshots (½ day) — D-10
- Re-take Phase-0 screenshots, diff visually.
- Update `README.md` and `docs/specs/spec-0001/` with new screenshots.
- Bump version `2.0.0 → 2.1.0` (additive UI; no breaking presenter changes).

**Total**: ~10–12 engineering days, splittable across two people. Each phase is independently mergeable.

---

## 4 · Risk Register

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| R-01 | QSS doesn't support drop-shadow → "soft elevation" looks flat | High | Use `QGraphicsDropShadowEffect` on top-level cards (KPI, insight). Accept ≤ 3 effects per screen to keep paint cost low. |
| R-02 | `QTextBrowser` SVG rendering quirks across DPIs | Medium | Pre-rasterise cut-bars via `QPainter` into PNG data-URIs when DPI ≠ 100%. Fall back to existing bar chart. |
| R-03 | Command palette steals focus from Tekla CLR dialogs | Low | Gate `Ctrl+K` to active main window; check `QApplication.activeModalWidget()` before opening. |
| R-04 | Dark theme regressions in third-party widgets we don't theme (file dialogs) | Medium | Accept native chrome for OS dialogs. Document. |
| R-05 | Reduced motion still leaks animations through Qt's built-in tooltips/menus | Low | Document scope: we control only our widgets, not Qt's internal animations. |
| R-06 | Translation drift between EN/PT for new keys | Medium | New keys land in **both** YAMLs in the same commit. Add a `pytest` test that asserts EN and PT have identical key sets (we already have something close in `test_i18n_load.py` — extend it). |
| R-07 | Snapshot/visual tests bloat the repo | Medium | Store screenshots under `docs/ui-mocks/baseline/` (already git-tracked but excluded from wheel via `pyproject.toml` packaging rules). PNG only, max ~200 KB each. |
| R-08 | Presenter-emitted dataclass leaks engine details into the view | Low | `OptimizationSummary` is a UI-facing read model in `models/`, populated from `NestResult`. The view never sees `NestResult` internals. |
| R-09 | Logo variants don't exist for dark mode | High | We already have `select_logo_variant`; ship a dark-on-light + light-on-dark PNG pair. Defer to branding owner. |
| R-10 | Win10 doesn't render Mica/acrylic — chrome looks "fake" | Medium | Use a flat translucent overlay (rgba) for "glass" — no native Mica calls. Looks consistent Win10/Win11. |

---

## 5 · Test Strategy

We keep the 240-test floor and grow it deliberately.

### 5.1 What gets a unit test
- Token contracts (both themes).
- ThemeService events.
- Command palette fuzzy matcher (pure function).
- `OptimizationSummary` derivation from `NestResult`.
- i18n key parity EN↔PT.
- Material chip delegate paint path (via `QPixmap` snapshot of a fixed-size table).

### 5.2 What gets a `pytest-qt` integration test
- Chrome contains all expected actions, both languages.
- `Ctrl+K` opens palette, selecting "Run nest" triggers `presenter.run_nest`.
- Theme switch redraws main window without losing splitter sizes.
- KPI strip updates when `optimization_summary_changed` fires.
- Unfit-pieces insight card lists piece IDs from `ProfileResult.unfit_pieces`.

### 5.3 What stays out of automated tests
- Pixel-perfect screenshot diffs. We document baselines but reviewer eyeballs them.
- Animations (timing-flaky). We assert "animation is configured" via attribute checks, not playback.

### 5.4 Coverage gates
- Maintain ≥ existing per-file coverage in `views/` and `design_system/`. New files must launch at ≥ 85%.
- `pytest --cov` config already in `pyproject.toml`; no tooling change needed.

---

## 6 · Performance Budget

| Action | Today (measured on baseline laptop) | Budget post-refactor |
|---|---|---|
| Cold start to `NestWindow.show()` | ~ 350 ms | ≤ 450 ms (theme build + palette index allowed +100 ms) |
| `presenter.run_nest` for 1k pieces | ~ 90 ms | unchanged (no engine touch) |
| Theme toggle round-trip | n/a | ≤ 80 ms perceived (pre-built sheets) |
| Command palette open | n/a | ≤ 60 ms perceived (lazy-built, cached after first open) |
| Memory at idle | ~ 110 MB | ≤ 130 MB |

Measurement harness: `tests/perf/` (new) — opt-in via `pytest -m perf`. Each metric is a soft warning, not a CI gate, in v2.1.

---

## 7 · Migration Order at a Glance

```
Phase 0 ── baseline screenshots
   │
Phase 1 ── tokens + ThemeService (no visual change)
   │
   ├── Phase 2 ── chrome split  ──┐
   ├── Phase 6 ── tables polish  ─┤  can run in parallel
   └── Phase 7 ── dark mode      ─┘  (all consume Phase 1)
   │
Phase 3 ── KPI binding (depends on 2)
   │
Phase 4 ── Command palette (depends on 2)
   │
Phase 5 ── Report polish (depends on 1, 3)
   │
Phase 8 ── Motion polish
   │
Phase 9 ── cleanup, screenshots, version bump
```

---

## 8 · Decisions (locked 2026-05-22)

| # | Question | Decision | Implication |
|---|---|---|---|
| Q1 | Navigation model | **Top chrome only**, no left rail | Splitter width on 1366px laptops preserved; no `QDockWidget` work |
| Q2 | Brand palette | **Adopt mockup palette**: brand colours unchanged (`#1d4ed8` / `#0f766e`); modernise neutrals, add surface tier, glass/overlay rgba, full dark scale | Token contract grows; brand-contrast tests stay green; new neutral-contrast tests added in Phase 1 |
| Q3 | AI insight cards | **Static heuristics only** in v2.1 | No network egress, no privacy review; rule-based suggestions live in `services/insights.py` (new) under existing license gate |
| Q4 | Command palette scope | **Commands only** | Reuses `design_system/commands.py:CommandDescriptor` registry; no MRU service, no jump-to-piece |
| Q5 | Reduced motion | **Preference only, default OFF** | New `AppConfig.prefer_reduced_motion: bool = False`; no Windows registry probing |
| Q6 | Status bar content | **Status text only** | `AmbientStatusBar` replaces `StatusBanner` 1:1; no license/version/telemetry surfaced in v2.1 |

These decisions update the phase scope:
- Phase 4 (command palette) loses ~½ day — no MRU.
- Phase 5 (report) gains `services/insights.py` with rule-based heuristics (~½ day).
- Phase 8 (motion) loses ~¼ day — no OS detection branch.

---

## 9 · Definition of Done

The refactor is done when:
- All 9 phases merged, version `2.1.0` cut.
- 240 → ≥ 280 tests, all green.
- Light + dark themes ship; system preference honoured.
- Command palette opens with Ctrl+K and triggers every command currently in menu+toolbar.
- Unfit-pieces are surfaced both in the HTML report **and** as an actionable card in the Qt report view (closes the loop on the May 2026 engine fix).
- `nest_window.py` ≤ 300 LOC; no single view file > 400 LOC.
- Screenshots in `docs/specs/spec-0001/` updated; release notes published.
- No regression in CLR/Tekla integration smoke tests.

---

*Last edited 2026-05-22. Owner: UI working group. Mockups: `docs/ui-mocks/`.*

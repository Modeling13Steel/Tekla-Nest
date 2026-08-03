# M7 · Dark mode rollout

**Branch**: `feat/ui-m7-dark-mode` (off `feat/ui-m6-tables`)
**Status**: 🟢 Done

## What this milestone does

Promotes dark mode from "service exists, but nothing reaches it" to a
fully user-facing toggle:

* **7a** — New `Preferences → Theme` menu (`QActionGroup`, exclusive)
  with three options: `System` · `Light` · `Dark`. Each selection
  routes through `ThemeService.apply(theme)` which persists the choice
  to `~/.tekla_nest/preferences.json` and re-emits `themeChanged` when
  the resolved theme actually changes.
* **7b** — The existing `AppChrome` theme button (cycle Light → Dark →
  System) is now wired to the same `ThemeService`. Toggle button and
  menu selection stay in sync via `set_theme()` + `setChecked()`.
* **7c** — `main.py` constructs the `ThemeService` once, hands it to
  `NestWindow`, and connects `themeChanged → app.setStyleSheet(...)`
  so a swap is O(1) (both stylesheets are pre-built on startup).
* **7d** — Dark palette validated against WCAG: 6 text-on-surface
  pairs hit AA (≥ 4.5:1), 7 UI / brand-accent pairs hit AA-large
  (≥ 3:1).

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/views/nest_menu.py` | `MenuBuilder` gains a `Preferences → Theme` submenu; new `theme_actions` dict on `MenuBuildResult`. |
| `src/tekla_nest/views/nest_window.py` | Accepts `theme_service: ThemeService`. New slots `_apply_theme` + `_on_theme_changed`. Chrome `theme_toggled` + menu actions both flow through `ThemeService.apply()`. |
| `src/tekla_nest/main.py` | Instantiates `ThemeService`, applies initial stylesheet, connects `themeChanged → app.setStyleSheet`. |
| `resources/languages/{en,pt}.yaml` | New keys: `menus.preferences`, `menus.theme`, `theme.{system,light,dark}` (EN/PT parity). |
| `tests/unit/test_theme_menu.py` | 5 pytest-qt tests — menu shape, dark action triggers apply, persistence across restart, PT localisation, chrome → service routing. |
| `tests/unit/test_dark_contrast.py` | 13 parametrised tests — every dark-palette text & UI pair passes WCAG AA. |

## Decisions explained

**Why route both chrome toggle and menu through `_apply_theme`?**
One slot, one persistence call, one place to keep menu + chrome state
in sync. Eliminates the "toggle says dark, menu still says light"
class of bug.

**Why pass `ThemeService` into `NestWindow` instead of singleton lookup?**
Testability. The fixture builds a service with a `tmp_path`-backed
preferences file so tests don't pollute `~/.tekla_nest/`. Production
wiring lives in `main.py` and is just two lines.

**Why split AA / AA-large thresholds?**
Per WCAG: body text needs 4.5:1, large/UI elements need 3:1. Dark
brand colours (cyan, accent) brightened for dark surfaces still
clear 3:1 against `bg_surface` but not 4.5:1 — that's correct
behaviour for UI accents, not text.

**Why no logo variant work?**
The brand layer (`design_system/brand.py:select_logo_variant`)
already handles dark backgrounds — verified by visual QA in M2. The
M7 spec lists it as optional; we don't ship a new dark logo asset
this milestone (placeholder is the existing dark-mode SVG). If
branding owners deliver a new dark variant later, it drops in by
file naming convention.

## Validation gate

| Gate | Result |
| --- | --- |
| `pytest -q` | **387 passed** (+18 over M6). |
| `ruff check src tests` | All checks passed. |
| `scripts/check_loc.py` | LOC budgets OK (`nest_window.py` 330 / 446). |
| EN/PT parity | 5 new keys, mirrored in both files. |
| Dark contrast | 13 / 13 token pairs meet AA. |

## What unblocks next

* **M8 motion** can fade between stylesheets on `themeChanged` for a
  polished swap instead of the current hard cut.
* **M9 release notes** can finally claim "fully themed app shell".

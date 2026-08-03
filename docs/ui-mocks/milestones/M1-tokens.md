# M1 — Design tokens (dark) + ThemeService foundation

> **Status:** 🟢 Done · **Branch:** `feat/ui-m1-tokens` (branched off `chore/ui-m0-baseline`)
> **Mock reference:** `docs/ui-mocks/styles.css` (palette section); see also `docs/ui-mocks/index.html` dark theme demo.

## What this milestone does

M1 lays the **foundation** for runtime light/dark theming without touching a single
pixel of the running app. The view layer is wired up in M7; M1 only adds the
parts that exist *underneath* the views:

1. **`Theme` enum** — `SYSTEM` / `LIGHT` / `DARK`, string-valued so it persists
   cleanly to JSON.
2. **Dark palette tokens** — `dark_color_tokens()` produces the mockup’s dark
   surfaces, brightened brand colours, and elevated shadow recipes.
3. **Motion + extended radii tokens** — `MotionTokens(fast_ms=120, base_ms=200)`
   and `RadiusTokens.field/card/pill`, ready for M8 micro-interactions and M2
   cards / pills.
4. **`build_design_tokens_for_theme(cfg, theme)`** — an explicit-theme builder
   that ignores the legacy `cfg.background` dark-inversion hack but still
   honours `cfg.primary_color` / `cfg.accent_color`.
5. **`theme.py` refactor** — `_render_stylesheet(tokens)` factored out so both
   the legacy path (`build_app_stylesheet`) and the new themed path
   (`build_themed_stylesheet`) reuse one template. Light output is **byte-identical**
   to v2.0 (locked by a test).
6. **`build_all_stylesheets(cfg)`** — pre-builds both QSS strings once so a
   runtime theme swap is a single `QApplication.setStyleSheet` call.
7. **`ThemeService`** (`services/theme_service.py`) — a `QObject` that owns the
   current choice, persists it to `~/.tekla_nest/preferences.json`, resolves
   `SYSTEM` against `QGuiApplication.styleHints().colorScheme()`, and emits
   `themeChanged(Theme)` only when the *resolved* theme actually changes.

## Artefacts

| Path | Role |
| --- | --- |
| `src/tekla_nest/design_system/tokens.py` | Token dataclasses, `Theme` enum, dark factory, both builders |
| `src/tekla_nest/design_system/__init__.py` | Re-exports `Theme`, `dark_color_tokens`, `build_design_tokens_for_theme` |
| `src/tekla_nest/theme.py` | `_render_stylesheet` + 3 entry points: `build_app_stylesheet` (legacy), `build_themed_stylesheet`, `build_all_stylesheets` |
| `src/tekla_nest/services/theme_service.py` | `ThemeService(QObject)` — apply / current / resolved / stylesheet + persistence |
| `tests/unit/test_design_tokens_dark.py` | 5 tests · hex shape + AA contrast |
| `tests/unit/test_theme_build.py` | 5 tests · selector coverage + legacy-equality lock |
| `tests/unit/test_theme_service.py` | 9 tests · signals + persistence + SYSTEM resolution |

## Decisions explained

- **Light palette deliberately unchanged.** Mockup palette values are added as
  *additive* token fields (`text_secondary`, `bg_surface_2`, `border_soft`,
  glass/overlay, shadow recipes). Existing widgets see no diff; M2 widgets
  opt-in. This satisfies the M1 DoD “no visual change” without losing the
  research from REFACTOR_PLAN §8 Q2.
- **`cfg.background` dark-inversion is preserved in the legacy path only.**
  The explicit-theme path (`build_design_tokens_for_theme`) ignores it — the
  `Theme` argument is authoritative. That keeps the colour-customisation
  dialog working byte-identically while letting M7 wire a real theme menu.
- **`SYSTEM` resolution lives in the service, not the tokens module.** The
  tokens layer must stay importable without a `QGuiApplication`; only the
  service touches `QGuiApplication.styleHints()`.
- **Stylesheets are pre-built once.** Theme swaps then reduce to a single
  string lookup + `setStyleSheet` call, well inside the 16 ms frame budget.
- **`themeChanged` fires on resolved change only.** Calling `apply(SYSTEM)`
  while the resolver still maps to `LIGHT` is a no-op for listeners — they
  do not have to deduplicate themselves.
- **Preference persistence is best-effort.** A failed write to
  `~/.tekla_nest/preferences.json` must never crash the app (try/except OSError).

## Validation gate

| Check | Result |
| --- | --- |
| `pytest -q` | **259 passed** (M0 baseline 240 → +19 new) |
| `ruff check src tests` | **All checks passed** |
| `scripts/check_loc.py` | **LOC budgets OK** (`tokens.py` 268, `theme.py` 289, both under 300) |
| Coverage (new modules) | `theme_service.py` **92%** · `theme.py` **90%** · `tokens.py` ≥95% (gate ≥85%) |
| Back-compat | `build_app_stylesheet(cfg) == build_themed_stylesheet(cfg, Theme.LIGHT)` byte-for-byte |

## Notes for reviewers

- `main.py` is **not** modified in M1. The app still bootstraps with
  `build_app_stylesheet(cfg)`; the menu entry that calls `ThemeService.apply()`
  lands in M7.
- `MotionTokens` is unused in M1 by design. It is wired into widgets in M8.
- If you add a token field, add a default — `ColorTokens` is a frozen dataclass
  and every legacy call site relies on `ColorTokens()` working with no args.

## What unblocks next

- **M2** can now consume `Theme`, `bg_surface_2`, `border_soft`, and the new
  radii to rebuild the app shell and toolbar without touching the legacy QSS.
- **M7** can drop in a View → Theme menu that calls `ThemeService.apply(...)`
  and hooks `themeChanged` to `QApplication.setStyleSheet`.
- **M8** can read `MotionTokens` for the micro-interaction layer.

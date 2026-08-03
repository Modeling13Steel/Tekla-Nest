# M8 · Motion + reduced-motion preference

**Branch**: `feat/ui-m8-motion` (off `feat/ui-m7-dark-mode`)
**Status**: 🟢 Done

## What this milestone does

Adds subtle motion to three high-traffic surfaces, gated by a single
preference so users with motion sensitivity (or low-spec hardware)
can opt out at runtime.

* **8a** — `design_system/motion.py` exposes two helpers:
  * `animate(target, prop, *, duration_ms, start, end)` — returns a
    configured `QPropertyAnimation` *or* `None` when reduced-motion is
    on (in which case the end value is applied synchronously).
  * `animate_value(*, duration_ms, start, end, on_update)` — returns
    a `QVariantAnimation` for numeric tweens (KPI count-up).
  * Both helpers hard-cap duration at **200 ms** and reject anything
    above; sluggish motion can't ship by accident.
* **8b** — `AppConfig.prefer_reduced_motion: bool = False`, loadable
  from the `app:` section of `config.yaml`. `_apply_reduced_motion`
  on `NestWindow` persists changes to `~/.tekla_nest/preferences.json`
  and updates the live `AppConfig` so the toggle takes effect without
  restart.
* **8c** — Three animations wired through the helpers:
  * **KPI count-up** (180 ms, `OutCubic`) on every `set_summary`.
    The authoritative formatted text is committed synchronously
    *before* the tween starts, so a11y tools and tests see the final
    value immediately; the tween only supplements the visual.
  * **Command palette fade-in** (120 ms) on `showEvent` —
    `windowOpacity` 0 → 1.
  * **Insight sidebar reveal** (200 ms) on `set_insights` via
    `QGraphicsOpacityEffect.opacity` 0 → 1.
* **8d** — `Preferences → Reduced motion` toggle (checkable QAction)
  added after the Theme submenu. EN/PT localised.

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/design_system/motion.py` | `animate`, `animate_value`, `is_reduced_motion`. 200 ms cap is enforced as a `ValueError`. |
| `src/tekla_nest/config/app_config.py` | `prefer_reduced_motion: bool` field + `app.prefer_reduced_motion` loader. |
| `src/tekla_nest/views/widgets/kpi_strip.py` | `_count_up_to()` tweens cards from last value to new; final text is committed synchronously for tests/a11y. |
| `src/tekla_nest/views/command_palette.py` | `showEvent` triggers 120 ms fade-in. |
| `src/tekla_nest/views/widgets/insight_sidebar.py` | `_play_reveal()` uses `QGraphicsOpacityEffect` for a 200 ms fade. |
| `src/tekla_nest/views/nest_menu.py` | `MenuBuilder` accepts `on_reduced_motion_change`; result now exposes `reduced_motion_action`. |
| `src/tekla_nest/views/nest_window.py` | New slot `_apply_reduced_motion` (live AppConfig mutation + JSON persist). |
| `resources/languages/{en,pt}.yaml` | New key `preferences.reduced_motion` (EN/PT parity). |
| `tests/unit/test_motion_helper.py` | 7 tests — default off, animate returns animation, reduced-motion bypass, 200 ms cap, animate_value callback. |

## Decisions explained

**Why a hard 200 ms cap?**
The roadmap mock spec says "no animation exceeds 200ms". Encoding
that as a `ValueError` in `animate()` means review can't accidentally
land an 800 ms easeIn — the test suite catches it locally.

**Why commit final text *before* starting the tween?**
Two reasons. (1) The unit tests are synchronous: they call
`set_summary` then read `_value.text()` immediately. (2) Screen
readers don't read every intermediate frame. The visible tween is
nice-to-have; the authoritative text is must-have.

**Why two separate helpers (`animate` vs `animate_value`)?**
Qt has two distinct animation classes for two distinct shapes:
`QPropertyAnimation` for "tween a property on a `QObject`" and
`QVariantAnimation` for "tween a value and tell me on each step".
Forcing them through one signature would compromise both. They share
the reduced-motion gate and the duration cap.

**Why persist `prefer_reduced_motion` separately from `config.yaml`?**
`config.yaml` is the deployment-time default; the runtime toggle
writes to the user's per-machine preferences file (same one
`ThemeService` already uses). On next start `AppConfig` re-reads
`config.yaml`, but a future M9 task can layer the prefs file on top
to make the user choice sticky across restarts. For M8, the toggle
takes effect immediately — sticky-across-restart is M9.

**Why `QGraphicsOpacityEffect` on the sidebar instead of
`windowOpacity`?**
`windowOpacity` only works on top-level windows. The sidebar is a
child of the report panel, so a graphics effect on the widget itself
is the correct surface.

## Validation gate

| Gate | Result |
| --- | --- |
| `pytest -q` | **394 passed** (+7 over M7). |
| `ruff check src tests` | All checks passed. |
| `scripts/check_loc.py` | LOC budgets OK (`nest_window.py` 358 / 446, `nest_menu.py` 217 / 400, `motion.py` 115 / 250). |
| EN/PT parity | 1 new key, mirrored in both files. |
| Max animation duration | 200 ms (sidebar reveal); KPI 180 ms; palette 120 ms. |

## What unblocks next

* **M9 release** can advertise "AA contrast in both themes, motion
  toggle, sub-200 ms animations" as accessibility headline features.
* Future motion surfaces (status-bar transition, table row insert)
  can adopt `animate()` directly without re-litigating the gate.

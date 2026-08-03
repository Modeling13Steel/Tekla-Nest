# M4 · Command Palette (Ctrl+K)

**Branch**: `feat/ui-m4-palette` (off `feat/ui-m3-kpi-binding`)
**Status**: 🟢 Done

## What this milestone does

Adds a Ctrl+K palette that lists every registered `QAction` and triggers
the same code path as menu/toolbar clicks. The palette is **the** way to
discover commands from the keyboard; it never duplicates command logic.

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/services/palette_ranker.py` | Pure scoring + history persistence. No Qt. |
| `src/tekla_nest/views/command_palette.py` | `CommandPalette(QDialog)` — search box + ranked list. |
| `src/tekla_nest/views/nest_window.py` | Wires `Ctrl+K` shortcut and `AppChrome.palette_requested → _open_palette`. |
| `src/tekla_nest/views/widgets/app_chrome.py` | Palette button now emits `palette_requested` (was disabled in M2). |
| `resources/languages/{en,pt}.yaml` | 8 new keys under `palette.*`. |
| `tests/unit/test_palette_ranker.py` | 13 tests — fuzzy scoring, recency, persistence, history cap. |
| `tests/unit/test_command_palette.py` | 11 pytest-qt tests — filter, disabled actions, keyboard, persistence. |

## Decisions explained

* **Fuzzy matcher is hand-rolled** (no `rapidfuzz`) — keeps the install
  footprint identical and meets ROADMAP §10.7. Sub-sequence match with
  consecutive-character and word-start bonuses.
* **Recency-decayed frequency** uses a one-week half-life. The integer
  rounding keeps the boost small (1–4 points) so a strong fuzzy match
  always outranks "I clicked this yesterday".
* **History stored in `~/.tekla_nest/preferences.json`**, capped at 100
  entries, sharing the file with `ThemeService` (M1). Tests redirect via
  monkeypatch on `palette_ranker._PREFS_PATH` — no test writes to HOME.
* **`QAction.trigger()` is the only invocation path.** Disabled and
  license-gated actions are filtered upstream (`isEnabled()` /
  `isVisible()` check in `candidates()`), so the palette automatically
  respects every gate the menu already does.
* **Keyboard model**: Esc closes; Enter activates current; arrows are
  forwarded to the list widget. No "fall-through to menubar" — the
  palette is modal.

## Validation gate

```
.venv/bin/python -m pytest -q                            # 334 passed
.venv/bin/python -m ruff check src tests                 # clean
.venv/bin/python scripts/check_loc.py                    # LOC budgets OK
.venv/bin/python -m pytest --cov=tekla_nest.services.palette_ranker
  --cov=tekla_nest.views.command_palette ...             # 95% / 97%
```

## Notes for reviewers

* The palette currently does **not** group by category. The mockup shows
  category labels but the ROADMAP keeps scope locked to "commands only"
  (Q4). Categories can be added later by partitioning on the
  `command_id` prefix.
* The shortcut hint in each row uses `QAction.shortcut().toString()`
  (Qt's native localisation), not a tr() string — Qt already maps
  `Ctrl` ↔ `⌘` per platform.
* `_open_palette` reuses an existing instance if already visible
  (avoids stacking palettes when the user mashes Ctrl+K).

## What unblocks next

M5 (report polish) can register additional commands (`filter_by_profile`,
`insert_stock_for_unfit`) and they appear in the palette automatically.
M8 will fade the dialog in (≤120ms) via `design_system/motion.py`.

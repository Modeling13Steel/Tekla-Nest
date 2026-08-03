# M6 · Tables polish (material chips + filter bar)

**Branch**: `feat/ui-m6-tables` (off `feat/ui-m5-report`)
**Status**: 🟢 Done

## What this milestone does

Lifts the Parts and Stock tables to the v2.1 mock spec:

* **6a** — A curated **material palette** (`design_system/material_palette.py`)
  maps the 6 common steel grades (S235JR, S275JR, S355JR, S355J2, S420,
  S460) to AA-contrast bg/fg pairs. Unknown grades hash into an 8-entry
  fallback pool so colour assignment is stable across runs.
* **6b** — `MaterialChipDelegate` paints the material column as a
  rounded pill (radius 10 px, 10×4 padding, antialiased). The delegate
  is auto-installed on any column whose `header_key` ends in
  `.material`.
* **6c** — `TableFilterBar` replaces the raw `QLineEdit` search row.
  Search input is **debounced at 150 ms** to avoid stuttering on large
  tables. A row of toggleable material chips is rendered next to the
  search box; selected chips AND with the search filter.
* **6d** — `TableFilterProxyModel` (extracted to its own module) gains
  `set_material_column(int)` and `set_materials(set[str])`. Filters
  compose: a row must match the text *and* be in the selected
  materials.
* **6e** — `QTableView::item` padding bumped to `spacing.sm` (8 px) for
  comfortable row rhythm; row height pinned to 32 px.

The Parts and Stock view classes are unchanged — auto-detection via
`header_key.endswith(".material")` does the wiring for both.

## Artefacts

| File | Purpose |
| --- | --- |
| `src/tekla_nest/design_system/material_palette.py` | 6 curated grades + 8-entry fallback pool, hash-stable. `material_color()`, `all_known_grades()`. |
| `src/tekla_nest/design_system/__init__.py` | Exports `MaterialColor`, `material_color`, `all_known_grades`. |
| `src/tekla_nest/views/widgets/material_chip_delegate.py` | `QStyledItemDelegate` painting pill chips. `sizeHint` min height 32 px. |
| `src/tekla_nest/views/widgets/table_filter_bar.py` | Search `QLineEdit` (debounced 150 ms) + toggleable material chips. Public API: `set_materials`, `current_text`, `current_materials`, `clear`, `retranslate`. |
| `src/tekla_nest/views/table_filter_proxy.py` | Extracted `TableFilterProxyModel`: text + material AND filter. |
| `src/tekla_nest/views/table_system.py` | Rewired `DataTableWidget` to use `TableFilterBar`, auto-detect material column, install delegate, row-height 32, synchronous `filter_text()` bypass for tests. |
| `src/tekla_nest/theme.py` | QSS `QTableView::item, QTableWidget::item` padding `spacing.sm`. |
| `tests/unit/test_material_chip_delegate.py` | 4 tests — paint, sizeHint, known grade, hash stability. |
| `tests/unit/test_table_filter_bar.py` | 5 tests — default state, dedupe, chip toggle, debounce, clear. |
| `tests/unit/test_table_filter_integration.py` | 5 tests — search narrows, chip filter, AND combo, stock chips, delegate attached. |
| `tests/unit/test_window_commands.py` | Updated path: `_search` now lives on `_filter_bar`. |

## Decisions explained

**Why hash-based palette assignment for unknown grades?**
The palette has 6 curated entries; any incoming grade outside that set
(custom alloys, future ASTM codes) hashes into an 8-entry pool. Hashing
keeps the colour stable for a given string across runs so the chip
appearance doesn't flicker when rows shuffle.

**Why 150 ms debounce?**
Empirical sweet spot — short enough to feel live, long enough to skip
intermediate keystrokes on 2000-row tables. The debounce is bypassed
when `filter_text()` is called programmatically so unit tests don't
need to wait for the timer to drain.

**Why `header_key.endswith(".material")` over a new `ColumnDefinition.role`?**
The two existing columns (`tables.parts.headers.material`,
`tables.stock.headers.material`) already share the suffix, and the
chip-rendering policy is "this is a material column" — exactly what
the suffix conveys. Adding a `role` field would touch every column
definition for one consumer. If a second policy needs the same hook
(e.g. priority badges), we'll promote to a role enum then.

**Why extract `TableFilterProxyModel`?**
`table_system.py` blew the 400-LOC budget once the proxy gained two
extra filter axes. Moving the proxy into its own module keeps the
view shell focused on layout/wiring and isolates the filter logic for
unit testing.

## Validation gate

| Gate | Result |
| --- | --- |
| `pytest -q` | **369 passed** (+14 over M5). |
| `ruff check src tests` | All checks passed. |
| `scripts/check_loc.py` | LOC budgets OK (`table_system.py` 396 / 400). |
| EN/PT parity | No new i18n keys this milestone. |

Coverage spot-checks on new modules:

| Module | Coverage |
| --- | --- |
| `design_system/material_palette.py` | 100% |
| `views/widgets/table_filter_bar.py` | 96% |
| `views/table_filter_proxy.py` | 100% |
| `views/widgets/material_chip_delegate.py` | 58% (paint path partially exercised; integration test covers real paint via live `QTableView`) |

## What unblocks next

* **M7 dark mode** can reuse the `MaterialColor.bg/fg` pairs — they're
  declared as design tokens, so a second palette table (dark) drops in
  next to the existing one without touching widget code.
* **M8 motion** has a natural hook on chip toggle (`materials_changed`)
  for chip-press feedback animations.

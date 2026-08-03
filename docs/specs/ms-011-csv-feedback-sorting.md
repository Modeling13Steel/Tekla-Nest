# Spec: ms-011 — CSV feedback visibility + material sort consistency

## Root causes found

### Bug A — CSV notice overwritten (no visible feedback)
`load_parts_from_csv` and `load_client_stock_csv` emit `notice` **before**
`_complete_operation()`.  `_complete_operation` synchronously emits
`operation_completed` → `_on_operation_completed` → `set_status("…completed", "success")`,
which overwrites the notice text immediately.  The user sees the generic
"Load stock CSV completed." message (or nothing perceptible before it) instead
of the count / empty notice.

Secondary: `_show_notice` passes level `"info"` to `set_status`.  `"info"` is
not in `_VALID_LEVELS`, so it falls back to `"ready"` styling (neutral grey dot),
making any notice that does survive look idle rather than informational.

### Bug B — material order inconsistent between tabs
`parts_loaded.emit` and `stock_loaded.emit` / `market_stock_replaced.emit` carry
lists in load-order (CSV row order, API iteration order, generator order).
The parts table and the stock table each display whatever arrives — often in
different orderings — so the same (profile, material) pair may appear at row 3
in parts and row 7 in stock.

## Functional requirements

- FR-001: After a successful CSV load, the status bar must show the count /
  empty notice with "success" styling, and that text must not be replaced by
  a generic "completed" message.
- FR-002: Parts rows must be ordered by `(profile ASC, material ASC)`.
  Within the same (profile, material) group the secondary key is `reference ASC`.
- FR-003: Stock rows (both market and client) must be ordered by
  `(profile ASC, material ASC, length ASC)`.
- FR-004: FR-002 and FR-003 must apply to every source of data: Tekla provider,
  parts CSV, stock CSV, and auto-populate.  Manual in-table edits need not
  trigger a re-sort.

## Non-functional requirements

- NFR-001: Sorting at the presenter level (before emitting signals) so all
  downstream consumers (table widget, PDF, Excel) receive pre-sorted data
  without each needing its own sort.
- NFR-002: No change to the `parts_loaded` or `stock_loaded` signal types.

## Acceptance criteria

- AC-001: Load a stock CSV with 3 entries. Status bar shows
  "3 stock entries loaded into the Client tab." with success styling.
- AC-002: Load a parts CSV with an empty file. Status bar shows the empty
  notice with success styling.
- AC-003: After loading parts, the parts table rows are sorted alphabetically
  by profile, then material.
- AC-004: After auto-populating stock, stock rows are sorted by profile, then
  material, then length.
- AC-005: For a result with profiles HEA240/S275 and IPE300/S235, the order
  in the parts table matches the order in the market stock table.

## Scope

### In scope
- `nest_presenter.py`: move `notice.emit` after `_complete_operation`; sort
  `self._parts` and stock lists before emitting.
- `nest_window.py` `_show_notice`: change level from `"info"` to `"success"`.

### Out of scope
- Re-sorting on manual table edits.
- Sorting the report profiles (already determined by optimization order).
- Adding "info" as a new valid status level (requires theme work, deferred).

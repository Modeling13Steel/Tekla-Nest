# Spec: ms-007 — Auto-stock Signal Fix + Material Scoping

## Purpose
Fix two bugs in `auto_populate_stock()`:
1. Clicking "Auto-stock" repeatedly appends duplicate entries instead of replacing market stock.
2. Stock is generated for every configured material (S235JR, S275JR, S355JR) regardless of what is
   actually used in the loaded parts — cluttering the stock table with irrelevant entries.

## Scope

### In scope
- Add `market_stock_replaced = Signal(list)` to `NestPresenter`.
- In `auto_populate_stock()`, emit `market_stock_replaced` instead of `stock_loaded`.
- Connect `market_stock_replaced` → `set_market_stock()` in `nest_window.py`.
- Change `generate_default_stock()` to accept `pairs: list[tuple[str, str]]`
  (profile, material) pairs extracted from parts, so only those exact combinations are seeded.
- Remove the now-redundant "belt-and-braces extras" loop from `auto_populate_stock()`
  (the new `generate_default_stock` handles exact pairs already).
- Keep the over-length bar seeding logic (it is unrelated to this bug).

### Out of scope
- CSV stock loading (`load_client_stock_csv`) — it correctly appends to client stock.
- Market stock loaded from CSV (`load_stock_csv`) — uses the same append semantics
  intentionally (user is adding to the market stock).
- Any UI changes beyond the signal wiring.

## Functional Requirements

- FR-001: Clicking "Auto-stock" any number of times must result in exactly one set of
  market-stock entries in the stock table — no duplication.
- FR-002: The generated stock entries must cover only the (profile, material) pairs that
  appear in the currently loaded parts — not all `cfg.materials`.
- FR-003: The over-length bar seed (bars sized to the longest piece per pair, rounded up
  to the next 500 mm) must still be applied after scoping.
- FR-004: Existing callers of `generate_default_stock` that only pass profiles (no materials)
  must be updated to pass pairs, or the function signature must remain backward-compatible.

## Non-Functional Requirements

- NFR-001: `stock_loaded` signal must still be emitted for CSV loading paths — only
  `auto_populate_stock()` should use the new `market_stock_replaced` signal.
- NFR-002: No change to `StockEntry` model or `StockTabsWidget` public API beyond the
  new signal connection.

## Acceptance Criteria

- AC-001 (FR-001): After calling `auto_populate_stock()` twice with the same parts, the
  stock table shows the same number of entries as after calling it once.
- AC-002 (FR-002): When parts all use `S355JR`, generated stock contains only `S355JR`
  entries (not S235JR or S275JR unless those are also in the parts).
- AC-003 (FR-003): When a part is longer than the longest stock bar for its
  (profile, material) pair, an extra bar sized ≥ the part length is added.
- AC-004 (NFR-001): CSV-loaded client stock still appends (not replaces) when called
  after `auto_populate_stock()`.

## Open Questions

### User standpoint
- None: the expected behaviour (replace vs append) was stated explicitly.

### Engineer standpoint
- Q: Should `load_stock_csv` also replace market stock, or append?
  A: Append — the user may load multiple CSV files to build up their market stock.

### System standpoint
- Q: Is `set_market_stock()` on `StockTabsWidget` idempotent / safe to call on empty list?
  A: Yes — it clears the market table and re-populates from the provided list.

## Related ADRs
- None required (implementation decision; no architecture trade-offs needed).

# Implementation Plan: ms-007 — Auto-stock Signal Fix + Material Scoping

## Branch
`ms-007-autostock-signal-fix` — rebased on `ms-006-pythonnet-compat-fix`

## Spec
[docs/specs/ms-007-autostock-signal-fix.md](../specs/ms-007-autostock-signal-fix.md)

## Tasks

- [ ] AC-001 / FR-001 — Add `market_stock_replaced = Signal(list)` to `NestPresenter` class body
- [ ] AC-001 — In `auto_populate_stock()`, replace `self.stock_loaded.emit(self._market_stock)` with `self.market_stock_replaced.emit(self._market_stock)`
- [ ] AC-001 — In `nest_window.py`, add `self._pres.market_stock_replaced.connect(self._stock_tabs.set_market_stock)` after the existing `stock_loaded` connection
- [ ] AC-002 / FR-002 — Change `generate_default_stock` signature from `profiles: list[str]` to `pairs: list[tuple[str, str]]`; update the loop body to iterate over pairs directly (no inner `cfg.materials` loop)
- [ ] AC-002 — In `auto_populate_stock()`, extract `pairs = sorted({(p.profile.strip(), (p.material or "").strip()) for p in self._parts if p.profile})` and pass to `generate_default_stock(pairs)`
- [ ] AC-002 — Remove the "belt-and-braces extras" loop (now redundant since `generate_default_stock` accepts exact pairs)
- [ ] AC-003 — Keep the over-length bar seeding loop (unchanged)
- [ ] Tests written and passing — see `docs/tests/ms-007/`
- [ ] Linters clean (`ruff check src/`)
- [ ] Acceptance criteria validated and results recorded in `docs/tests/ms-007/index.md`
- [ ] `git push -u origin ms-007-autostock-signal-fix`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | All code changes above | `claude-sonnet-4-6` |
| Test writer | pytest tests for AC-001 through AC-004 | `claude-haiku-4-5-20251001` |

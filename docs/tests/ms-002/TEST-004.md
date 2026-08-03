# TEST-004 — Subtotal rows are rendered bold

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-4 — All cells in a subtotal row use a bold `QFont`.

## Preconditions

- Any non-empty `NestResult`.

## Steps

1. Call `widget.set_result(result)`.
2. Identify a subtotal row by its position (last row of each profile group).
3. Call `item.font().bold()` for each cell in that row.

## Expected Result

- `item.font().bold()` is `True` for all 6 cells of the subtotal row.
- Data rows have `item.font().bold()` as `False` (default QFont).

## Automated test

The `_render` method applies `bold_font` (constructed via `QFont(); setBold(True)`)
only to `_SubtotalRow` instances. Verified by construction in code review;
a dedicated Qt font assertion can be added if regression is observed.

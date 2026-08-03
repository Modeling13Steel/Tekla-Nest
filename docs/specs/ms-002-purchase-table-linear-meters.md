# Spec: ms-002 — Purchase Table: Linear Meters Column and Per-Profile Subtotals

## Purpose
Bring the in-app purchase table to parity with the Excel and CSV exports by adding a "Linear m" column per row and per-profile subtotal rows, so the operator can immediately see how many linear meters of each profile to order.

## Scope

### In scope
- Add a "Linear m" column to `PurchaseTableWidget` showing `length × count / 1000` per row.
- Insert per-profile subtotal rows between profile groups (total bars + total linear meters for that profile), matching the existing Excel sheet layout.
- Update the i18n keys used for the new column header.
- Regression tests for the updated widget.

### Out of scope
- Changes to Excel or CSV export (already correct).
- Changes to the PDF report template.
- Changing the sort order of the table.
- Adding expand/collapse for profile groups (simple static subtotal rows are sufficient).

## Functional Requirements

- FR-001: The purchase table must display a "Linear m" column as the 6th column, showing `(length × count) / 1000` rounded to 2 decimal places for each row.
- FR-002: After the last row of each profile group, a subtotal row must appear showing: profile name, "—" for material/length/source, total bar count for that profile, total linear meters for that profile.
- FR-003: The grand-total label at the bottom of the widget must continue to show total bars and total linear meters across all profiles (no regression).
- FR-004: The subtotal rows must be visually distinct from data rows (bold text or a background tint).
- FR-005: Sorting must be disabled when subtotal rows are present (to avoid mixing subtotals with data rows).

## Non-Functional Requirements

- NFR-001: Re-render time for a result with ≤ 500 bars must remain under 100 ms.
- NFR-002: The widget must remain fully functional when `scope` filtering is applied — subtotals must reflect only the filtered rows.

## Acceptance Criteria

- AC-001 (FR-001): Given a result with one HEA200 bar of 6000 mm (count = 2), the "Linear m" cell for that row reads "12.00".
- AC-002 (FR-002): Given two rows for profile HEA200 (6000 mm × 2, 3000 mm × 1), a subtotal row appears after them showing count = 3 and linear m = 15.00.
- AC-003 (FR-003): The grand-total label at the bottom matches the sum of all per-row linear_m values.
- AC-004 (FR-004): Subtotal rows are visually distinguishable from data rows in the rendered widget.
- AC-005 (FR-005): Clicking a column header to sort does not reorder rows when subtotals are present (sorting disabled).
- AC-006 (NFR-002): When a scope filter is applied that includes only HEA200, subtotals reflect only HEA200 bars.

## Open Questions

### User standpoint
- Q: Should the subtotal row show the profile name again in the first column, or a label like "Subtotal HEA200"?
  - Assumed: profile name repeated, bold, for quick scanning.
- Q: Should per-profile subtotals also appear in the grand-total label, or only as inline rows?
  - Assumed: inline rows only; grand total label unchanged.

### Engineer standpoint
- Q: `QTableWidget.setSortingEnabled(False)` when subtotals are inserted — is this the right guard, or should we switch to a `QAbstractTableModel` to have full control over row identity?
  - For the scope of this milestone: disable sorting when subtotal rows exist. A model-based refactor is out of scope.
- Q: The `PurchaseRow` dataclass is a frozen dataclass; subtotal rows are not `PurchaseRow` instances. How to represent them in `_render()`?
  - Sentinel: use a `None` entry or a `SubtotalRow` dataclass in the internal `_rows` list to mark subtotal positions.

### System standpoint
- Q: Does disabling sorting affect accessibility (screen-reader column-sort announcements)?
  - Acceptable trade-off at this scope. Revisit if accessibility requirements are formalised.

## Related ADRs
None required — straightforward UI augmentation with no architectural trade-offs.

# Change Request Investigation — Feedback Round 2

Investigated: 2026-06-08
Investigator: Claude (orchestrator)

---

## Summary

| # | Request | Status | Evidence |
|---|---|---|---|
| 2 | Bar quantities and lengths in cutting plan | ✅ Already implemented | `report_template.html` lines 233-240; `bar_aggregation.aggregate_prep()` |
| 2.1 | Print/export only selected profiles | ✅ Already implemented | `nest_dialogs._ask_export_scope()`; scope applied to PDF, Excel, CSV |
| 3 | Delete rows in pieces table | ✅ Already implemented | `table_system.py` lines 208-423: delete button, keyboard shortcuts, context menu |
| 4 | Show purchase profile table after calculation | ✅ Already implemented | `PurchaseTableWidget` tab in `nest_window.py` lines 89-92, 286 |
| 5 | Attached image not exported in PDF | 🐛 Bug | Image is base64-encoded correctly but `QTextDocument.print_()` does not render `data:` URI images |
| 6 | Bar length and linear meters missing in purchase export | ❌ Gap in in-app table | Excel and CSV exports have bar length + linear_m + per-profile subtotals; in-app `PurchaseTableWidget` only shows profile, material, length_mm, source, count — missing linear_m column and per-profile subtotal rows |

---

## Detailed Findings

### ✅ Request 2 — Bar quantities and lengths in cutting plan

The PDF/HTML report already renders an "operator prep header" at the top of every profile section:

```
{count}× {length}mm  {count}× {length}mm  …  |  Total: N bars · X.XX m
```

Implemented via:
- `bar_aggregation.aggregate_prep()` → `ProfilePrep.by_length` (length, count tuples ordered longest-first)
- `report_template.html` lines 233-240 (`prep-header` div with `prep-chip` spans)
- Labels: `labels.prep_bar`, `labels.prep_total`

No work required.

---

### ✅ Request 2.1 — Export/print only selected profiles

All three export formats (PDF, Excel, CSV) already present a scope-selection dialog when the result contains ≥2 profiles.

- Dialog: `nest_dialogs._ask_export_scope()` — checkbox list of `(profile, material)` pairs
- Scope filtering: `bar_aggregation.filter_result(result, scope)` applied inside each export service
- Entry points: `prompt_export_pdf()`, `prompt_export_excel()`, `prompt_export_csv()` in `nest_dialogs.py`

No work required.

---

### ✅ Request 3 — Delete rows in pieces table

`table_system.DataTableWidget` (shared by both parts and stock tables) already has:
- A delete button that appears when ≥1 rows are selected (`table_system.py` line 211)
- `Delete` and `Backspace` keyboard shortcuts (lines 276-281)
- Right-click context menu with "Delete selected" action (lines 404-410)
- `rows_deleted` signal emitted with the count removed (line 401)

All wired into `PartsTableWidget` via `self._table_widget.rows_deleted.connect(self.rows_deleted)`.

No work required.

---

### ✅ Request 4 — Purchase profile table after calculation

`PurchaseTableWidget` is instantiated and added as a tab in the main result area in `nest_window.py`:

```python
self._purchase_table = PurchaseTableWidget()          # line 89
self._result_tabs.addTab(self._purchase_table, tr("purchase.tab"))  # line 92
```

It is populated after every run:
```python
self._purchase_table.set_result(result)  # line 286
```

Columns shown: Profile · Material · Length (mm) · Source · Count.

No work required.

---

### 🐛 Request 5 — Attached image not exported in PDF

**Root cause:** The rendering pipeline correctly base64-encodes the image and embeds it as a `data:` URI in the HTML template. The in-app `QTextBrowser` preview renders this correctly. However, when `export_pdf()` creates a `QTextDocument`, sets the HTML via `doc.setHtml(html)`, and calls `doc.print_(printer)`, Qt's text document renderer does not process `data:` URI images — they are silently dropped.

This is a known Qt limitation: `QTextDocument`'s internal resource loading mechanism (`loadResource()`) does not recognise the `data:` URI scheme for `<img>` tags.

**Files involved:**
- `src/tekla_nest/services/pdf_report.py` — produces HTML with `data:` URI image
- `src/tekla_nest/presenters/nest_presenter.py` lines 479-494 — `export_pdf()` uses `QTextDocument`
- `resources/report_template.html` lines 317-323 — image rendering block

**Spec and ADR:** [docs/specs/ms-001-pdf-image-export-fix.md](../specs/ms-001-pdf-image-export-fix.md), [docs/archive/adr/0001-pdf-image-qtextdocument.md](../archive/adr/0001-pdf-image-qtextdocument.md)

---

### ❌ Request 6 — Linear meters and per-profile subtotals in purchase table

**Excel and CSV exports already have this.** Both include:
- Bar length column per row
- Linear meters per row (length × count / 1000)
- Per-profile subtotal rows

**The in-app `PurchaseTableWidget` is missing:**
1. A "Linear m" column (length × count / 1000) per row — the `PurchaseRow.linear_m` property exists but is not shown
2. Per-profile subtotal rows showing total linear meters and total bars for that profile

The `ProfilePrep` dataclass (`bar_aggregation.py` line 59) and `grand_totals()` (line 170) already provide the required aggregated data.

**Files involved:**
- `src/tekla_nest/views/purchase_table.py` — needs linear_m column + subtotal rows
- `src/tekla_nest/services/bar_aggregation.py` — data already available, no changes needed

**Spec:** [docs/specs/ms-002-purchase-table-linear-meters.md](../specs/ms-002-purchase-table-linear-meters.md)

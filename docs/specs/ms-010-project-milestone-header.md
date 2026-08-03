# Spec: ms-010 — Tekla Project Name + Milestone in Export Headers

## Purpose
Two related features that both feed into the PDF and Excel report headers:

1. **Tekla project name**: When parts are loaded from Tekla, read the active model's project
   name from `Model.GetProjectInfo().Name` and display it on every export.
2. **Milestone text box**: Add a text input to the PDF and Excel export dialogs so the user
   can type a milestone/revision label that appears in the exported file header.

## Scope

### In scope
- Add `get_project_name(model) -> str` helper to `tekla_api.py`.
- Extend `tekla_extract.py` (subprocess helper) to output
  `{"parts": [...], "project_name": "..."}` instead of a bare list.
- Update `TeklaPartProvider` to populate `self.project_name` from both load paths
  (in-process and subprocess).
- Add `_project_name: str` and `_milestone: str` to `NestPresenter`; expose as read/write
  properties. `_project_name` is set after Tekla load; `_milestone` is set by the dialog.
- Add `project_name` and `milestone` parameters to `render_report_html()` and
  `export_excel()`.
- Update `report_template.html` to show project name and milestone in the header when
  non-empty.
- Update `excel_report.py` Summary sheet to include project name and milestone rows in the
  header area.
- Add `QInputDialog.getText()` milestone step to `prompt_export_pdf` and
  `prompt_export_excel` in `nest_dialogs.py`, pre-filled with the presenter's last milestone.
- Add i18n keys for the new labels in `en.yaml` and `pt.yaml`.

### Out of scope
- CSV export header (CSV format does not have a styled header; out of scope).
- Reading project name from non-Tekla sources (manual/CSV part loading leaves project
  name empty — that is correct behaviour; the field is simply omitted from the header).
- Persisting milestone across app restarts (session-only is sufficient).
- Reading any other Tekla `ProjectInfo` fields (description, designer, number).

## Functional Requirements

- FR-001: After loading parts from Tekla, `presenter.project_name` contains the value of
  `Model.GetProjectInfo().Name`, trimmed, or `""` if unavailable.
- FR-002: Before exporting PDF or Excel, the export dialog asks for a milestone string.
  The input is pre-filled with the last value the user typed in this session.
- FR-003: If the user clears the milestone field and confirms, the milestone is treated as
  empty and omitted from the header.
- FR-004: The PDF header must show project name (if non-empty) and milestone (if non-empty)
  below the company name / generated-at line.
- FR-005: The Excel Summary sheet header rows must show project name (if non-empty) and
  milestone (if non-empty) before the profile data table.
- FR-006: If `GetProjectInfo()` raises or returns `None`, `project_name` falls back to `""`.
  The export still proceeds without the project name.

## Non-Functional Requirements

- NFR-001: The subprocess helper change must be backward-compatible: the helper version check
  is internal, so both the helper and the in-process path must be updated atomically.
- NFR-002: No change to `PartProvider.get_parts()` return type — project name is a
  side-effect attribute, not part of the `list[PartEntry]` return value.
- NFR-003: `render_report_html` and `export_excel` must default `project_name=""` and
  `milestone=""` so all existing callers continue to work without changes.

## Acceptance Criteria

- AC-001 (FR-001): After calling `TeklaPartProvider.get_parts()` in-process on a connected
  model, `provider.project_name` is a non-None string (empty if name not available).
- AC-002 (FR-002/003): `prompt_export_pdf` shows a `QInputDialog` for milestone; pressing
  OK with text T → `presenter.milestone == T`; pressing Cancel → export aborted.
- AC-003 (FR-004): With `project_name="PROJ-42"` and `milestone="RC1"`, the rendered HTML
  contains both strings.
- AC-004 (FR-005): With `project_name="PROJ-42"` and `milestone="RC1"`, the exported Excel
  workbook's Summary sheet contains both strings in the first few rows.
- AC-005 (FR-006): Calling `get_project_name(model)` on a model where `GetProjectInfo()`
  raises returns `""` and does not propagate the exception.
- AC-006 (NFR-001): `tekla_provider.py` `_load_via_subprocess` correctly parses both the
  old bare-list format and the new dict format (for robustness during rollout).

## Open Questions

### User standpoint
- Q: Should the milestone field be shown for CSV export too?
  A: No — CSV does not have a styled header; out of scope.
- Q: What if the user presses Cancel on the milestone dialog?
  A: Cancelling aborts the export entirely (same as cancelling the scope or file dialog).
- Q: Should project name be editable by the user before export?
  A: No — it is read-only from Tekla. The user can only edit milestone.

### Engineer standpoint
- Q: What is the Tekla API call for project name?
  A: `model.GetProjectInfo().Name` — available in Tekla Open API 2021+.
  `GetProjectInfo()` returns a `Tekla.Structures.Model.ProjectInfo` object whose `.Name`
  property is a .NET string. Via pythonnet: `str(info.Name)`.
- Q: Does GetProjectInfo work in both in-process and subprocess paths?
  A: Yes — the subprocess `tekla_extract.py` runs with access to the Tekla model and can
  call `model.GetProjectInfo()` the same way.
- Q: What if `info.Name` is a .NET `null`?
  A: `str(None)` returns `"None"` in Python. Guard: `str(info.Name or "")`.

### System standpoint
- Q: Does changing the subprocess JSON format break the frozen binary before redeployment?
  A: Only if the old frozen binary calls the new helper. Guard: parse with
  `data = json.loads(stdout); parts = data["parts"] if isinstance(data, dict) else data`.
- Q: Is `Tekla.Structures.Model.ProjectInfo` available in all supported Tekla versions?
  A: Yes — `Model.GetProjectInfo()` has been in the Open API since at least Tekla 2019.

## Related ADRs
- None required (no architectural trade-off; straightforward extension of existing patterns).

# Implementation Plan: ms-010 — Tekla Project Name + Milestone in Export Headers

## Branch
`ms-010-project-milestone-header` — rebased on `ms-009-ux-error-fixes`

## Spec
[docs/specs/ms-010-project-milestone-header.md](../specs/ms-010-project-milestone-header.md)

## Tasks

### Tekla project name
- [ ] AC-005 — In `tekla_api.py`, add `get_project_name(model) -> str`:
  ```python
  def get_project_name(model) -> str:
      try:
          info = model.GetProjectInfo()
          return str(info.Name or "").strip()
      except Exception:
          return ""
  ```
- [ ] AC-001 — In `tekla_extract.py`, call `model.GetProjectInfo()` after connecting;
  change `json.dump(parts, sys.stdout)` to
  `json.dump({"parts": parts, "project_name": project_name}, sys.stdout)`
- [ ] AC-001 — In `TeklaPartProvider`, add `self.project_name: str = ""` attribute
- [ ] AC-001 — In `_load_via_subprocess`: parse `data = json.loads(proc.stdout)`;
  set `self.project_name = data.get("project_name", "")` if dict, else leave empty
  (backward-compatible: `parts = data["parts"] if isinstance(data, dict) else data`)
- [ ] AC-001 — In `_load_in_process`: call `get_project_name(model)` and store on self
- [ ] In `NestPresenter.__init__`, add `self._project_name: str = ""` and
  `self._milestone: str = ""`
- [ ] Add `project_name` read-only property and `milestone` read/write property to
  `NestPresenter`
- [ ] In `load_parts_from_provider()`, after `self._parts = self._part_provider.get_parts()`,
  add: `self._project_name = getattr(self._part_provider, "project_name", "")`

### Milestone dialog
- [ ] AC-002 — In `nest_dialogs.py` `prompt_export_pdf`, after `_ask_export_scope`:
  show `QInputDialog.getText(parent, tr("dialogs.milestone.title"), tr("dialogs.milestone.label"), text=presenter.milestone)`;
  if cancelled → return ""; on confirm → `presenter.milestone = text`
- [ ] AC-002 — Same change in `prompt_export_excel`
- [ ] Add i18n keys `dialogs.milestone.title` and `dialogs.milestone.label` to en.yaml + pt.yaml

### PDF header
- [ ] AC-003 — Add `project_name: str = ""` and `milestone: str = ""` parameters to
  `render_report_html()` (with defaults for backward compatibility)
- [ ] Pass them to the Jinja2 template context
- [ ] Update `report_template.html` header block to show project name and milestone
  when non-empty (below the `generated_at` line)
- [ ] Add i18n keys `report.project_name` and `report.milestone` to en.yaml + pt.yaml
  (labels for the PDF header lines)
- [ ] In `NestPresenter.export_pdf()` and `generate_report()`, pass
  `project_name=self._project_name, milestone=self._milestone` to `render_report_html`

### Excel header
- [ ] AC-004 — Add `project_name: str = ""` and `milestone: str = ""` parameters to
  `export_excel()` (with defaults)
- [ ] In Summary sheet, before the column headers, insert rows for project name
  and milestone when non-empty
- [ ] In `NestPresenter.export_excel()`, pass
  `project_name=self._project_name, milestone=self._milestone`

### Tests
- [ ] Tests written in `tests/test_ms010_project_milestone.py`
- [ ] Test docs in `docs/tests/ms-010/index.md` + TEST-001 through TEST-006
- [ ] Linters clean (`ruff check src/`)
- [ ] `git push -u teklanest ms-010-project-milestone-header`

## Subagent dispatch

| Agent | Task | Model |
|---|---|---|
| Implementer | All code changes above | `claude-sonnet-4-6` |
| Test writer | pytest tests AC-001 through AC-006 | `claude-haiku-4-5-20251001` |

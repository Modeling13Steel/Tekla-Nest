"""Tests for ms-010: Tekla project name + milestone in export headers.

Acceptance criteria covered:
  AC-001 — TeklaPartProvider.project_name is a str after get_parts() call.
  AC-002 — presenter.milestone setter/getter work correctly.
  AC-003 — render_report_html includes project_name and milestone in HTML.
  AC-004 — export_excel writes project_name and milestone to Summary sheet.
  AC-005 — get_project_name returns "" and does not raise on failure.
  AC-006 — _load_via_subprocess parses both list and dict JSON formats.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_result():
    from tekla_nest.models.bar_result import BarResult
    from tekla_nest.models.nest_result import NestResult, ProfileResult

    bar = BarResult(
        original_length=6000.0,
        mark="B1",
        material="S275JR",
        source="stock",
        cuts=[3000.0, 2500.0],
        cut_marks=["P1", "P2"],
    )
    prof = ProfileResult(
        profile="HEA240",
        bars=[bar],
        waste_pct=8.3,
        scrap_pct=0.0,
        unfit_pieces=[],
        material="S275JR",
    )
    return NestResult(profiles=[prof])


# ---------------------------------------------------------------------------
# AC-005: get_project_name swallows exceptions and returns ""
# ---------------------------------------------------------------------------


def test_get_project_name_returns_empty_on_exception():
    """get_project_name must return '' when GetProjectInfo() raises."""
    from tekla_nest.services.tekla_api import get_project_name

    class _BadModel:
        def GetProjectInfo(self):
            raise RuntimeError("not connected")

    assert get_project_name(_BadModel()) == ""


def test_get_project_name_returns_empty_on_none_name():
    """get_project_name must return '' when ProjectInfo.Name is None."""
    from tekla_nest.services.tekla_api import get_project_name

    class _Info:
        Name = None

    class _OkModel:
        def GetProjectInfo(self):
            return _Info()

    assert get_project_name(_OkModel()) == ""


def test_get_project_name_returns_stripped_name():
    """get_project_name returns the stripped project name string."""
    from tekla_nest.services.tekla_api import get_project_name

    class _Info:
        Name = "  PROJ-42  "

    class _OkModel:
        def GetProjectInfo(self):
            return _Info()

    assert get_project_name(_OkModel()) == "PROJ-42"


# ---------------------------------------------------------------------------
# AC-001: TeklaPartProvider has a project_name attribute after instantiation
# ---------------------------------------------------------------------------


def test_tekla_provider_has_project_name_attribute():
    """TeklaPartProvider must expose a project_name str attribute."""
    from tekla_nest.providers.tekla_provider import TeklaPartProvider

    provider = TeklaPartProvider()
    assert isinstance(provider.project_name, str)
    assert provider.project_name == ""


# ---------------------------------------------------------------------------
# AC-006: subprocess JSON parsing — list (old) and dict (new)
# ---------------------------------------------------------------------------


def test_subprocess_parse_dict_format(monkeypatch):
    """_load_via_subprocess parses new {"parts": [...], "project_name": "..."} format."""
    import json
    from unittest.mock import MagicMock, patch

    from tekla_nest.providers.tekla_provider import TeklaPartProvider

    provider = TeklaPartProvider()

    payload = {
        "parts": [
            {"reference": "1/A", "length": 3000.0, "profile": "HEA240", "material": "S275JR"}
        ],
        "project_name": "PROJ-42",
    }
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = json.dumps(payload)

    with (
        patch("tekla_nest.providers.tekla_provider._find_bundled_python", return_value=None),
        patch(
            "tekla_nest.providers.tekla_provider._find_system_python",
            return_value="/usr/bin/python3",
        ),
        patch("tekla_nest.providers.tekla_provider._find_helper_script", return_value="/tmp/x.py"),
        patch("subprocess.run", return_value=proc),
    ):
        raw, project_name = provider._load_via_subprocess("/fake/bin")

    assert project_name == "PROJ-42"
    assert len(raw) == 1
    assert raw[0]["reference"] == "1/A"


def test_subprocess_parse_list_format(monkeypatch):
    """_load_via_subprocess must handle old bare-list format gracefully."""
    import json
    from unittest.mock import MagicMock, patch

    from tekla_nest.providers.tekla_provider import TeklaPartProvider

    provider = TeklaPartProvider()

    old_payload = [
        {"reference": "2/B", "length": 6000.0, "profile": "IPE300", "material": "S235JR"}
    ]
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = json.dumps(old_payload)

    with (
        patch("tekla_nest.providers.tekla_provider._find_bundled_python", return_value=None),
        patch(
            "tekla_nest.providers.tekla_provider._find_system_python",
            return_value="/usr/bin/python3",
        ),
        patch("tekla_nest.providers.tekla_provider._find_helper_script", return_value="/tmp/x.py"),
        patch("subprocess.run", return_value=proc),
    ):
        raw, project_name = provider._load_via_subprocess("/fake/bin")

    assert project_name == ""
    assert len(raw) == 1
    assert raw[0]["reference"] == "2/B"


# ---------------------------------------------------------------------------
# AC-002: presenter milestone setter/getter
# ---------------------------------------------------------------------------


def test_presenter_milestone_default_empty():
    """presenter.milestone defaults to ''."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    p = NestPresenter()
    assert p.milestone == ""


def test_presenter_milestone_setter():
    """presenter.milestone = value is persisted across accesses."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    p = NestPresenter()
    p.milestone = "RC1"
    assert p.milestone == "RC1"


def test_presenter_milestone_setter_none_becomes_empty():
    """Setting milestone to None-like value normalises to ''."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    p = NestPresenter()
    p.milestone = None  # type: ignore[assignment]
    assert p.milestone == ""


def test_presenter_project_name_default_empty():
    """presenter.project_name defaults to ''."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    p = NestPresenter()
    assert p.project_name == ""


# ---------------------------------------------------------------------------
# AC-003: render_report_html includes project_name and milestone
# ---------------------------------------------------------------------------


def test_render_report_html_includes_project_and_milestone():
    """With project_name and milestone, rendered HTML contains both strings with labels."""
    from tekla_nest.services.pdf_report import render_report_html

    result = _minimal_result()
    html = render_report_html(
        result,
        project_name="PROJ-42",
        milestone="RC1",
    )
    assert "PROJ-42" in html
    assert "RC1" in html
    # labels prefix should be present
    assert "Project Name" in html or "Nome do projeto" in html
    assert "Milestone" in html or "Marco" in html


def test_render_report_html_omits_empty_project_and_milestone():
    """With empty strings, HTML must not contain any spurious placeholder text."""
    from tekla_nest.services.pdf_report import render_report_html

    result = _minimal_result()
    html = render_report_html(result, project_name="", milestone="")
    assert "PROJ-42" not in html


# ---------------------------------------------------------------------------
# AC-004: export_excel writes project_name and milestone to Summary sheet
# ---------------------------------------------------------------------------


def test_export_excel_summary_contains_project_and_milestone(tmp_path):
    """export_excel must write prefixed project_name and milestone to the Summary sheet."""
    from openpyxl import load_workbook
    from tekla_nest.services.excel_report import export_excel

    result = _minimal_result()
    out = tmp_path / "test.xlsx"
    export_excel(result, out, project_name="PROJ-42", milestone="RC1")

    wb = load_workbook(str(out))
    summary = wb.active
    all_values = [str(cell.value or "") for row in summary.iter_rows() for cell in row]
    assert any("PROJ-42" in v for v in all_values), "project_name not in Summary sheet"
    assert any("RC1" in v for v in all_values), "milestone not in Summary sheet"
    # label prefixes must be present
    assert any("Project Name" in v or "Nome do projeto" in v for v in all_values), (
        "project_name label not in Summary sheet"
    )
    assert any("Milestone" in v or "Marco" in v for v in all_values), (
        "milestone label not in Summary sheet"
    )


def test_export_excel_summary_without_project_milestone(tmp_path):
    """export_excel with empty project_name and milestone must not error."""
    from openpyxl import load_workbook
    from tekla_nest.services.excel_report import export_excel

    result = _minimal_result()
    out = tmp_path / "test_empty.xlsx"
    export_excel(result, out, project_name="", milestone="")

    wb = load_workbook(str(out))
    assert wb.active is not None

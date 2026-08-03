"""HTML report generation using Jinja2 templates.

Migrated from: C# RDLC ReportViewer + Report1.rdlc + DataSet1.
Replaces the binary RDLC format with a Jinja2 HTML template that
can be viewed in QTextBrowser and printed/exported to PDF.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path

from tekla_common.config.app_config import get_config
from tekla_common.design_system.brand import select_logo_variant
from tekla_common.design_system.tokens import build_design_tokens

from ..models import NestResult
from .report_labels import report_labels

LOGGER = logging.getLogger(__name__)


class ReportError(Exception):
    """Raised when report generation fails.

    Messages include what went wrong and how to fix it.
    """


def render_report_html(
    result: NestResult,
    output_path: Path | str | None = None,
    attached_image_path: Path | str | None = None,
    scope: frozenset[tuple[str, str]] | None = None,
    project_name: str = "",
    milestone: str = "",
) -> str:
    """Render nesting result to HTML string using the report template.

    ``scope`` (feedback v2 #2.1) filters the result to a subset of
    ``(profile, material)`` pairs before rendering. ``None`` keeps the
    full result; an empty frozenset renders an empty report.

    The template receives:
      - config (title, company, logo as base64)
      - result (NestResult with all profile data)
      - generated_at (timestamp)
      - attached_image_{b64,mime,name} (feedback v2 #5)

    Args:
        result: The NestResult to render.
        output_path: If given, also writes the HTML to this file.
        attached_image_path: Optional site image to embed in the report.

    Returns:
        The rendered HTML string.

    Raises:
        ReportError: If the template is missing or Jinja2 is not installed.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        raise ReportError(
            "Jinja2 is not installed. Run:  uv pip install Jinja2   (or:  pip install Jinja2)"
        )

    cfg = get_config()
    labels = report_labels(cfg)
    tokens = build_design_tokens(cfg)

    template_path = cfg.report_template_path
    if not template_path.exists():
        raise ReportError(
            f"Report template not found at '{template_path}'.\n"
            f"  Fix: Create the file or update 'report.template' in config.yaml.\n"
            f"  Expected: an HTML file with Jinja2 template syntax."
        )

    template_dir = str(template_path.parent)
    template_name = template_path.name

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
    )
    template = env.get_template(template_name)

    # Encode logo as base64 for embedding in HTML
    logo_b64 = ""
    logo_mime = "image/png"
    report_logo_path = select_logo_variant(cfg.report_logo_path, tokens.colors.bg_surface)
    if report_logo_path.exists():
        logo_bytes = report_logo_path.read_bytes()
        logo_b64 = base64.b64encode(logo_bytes).decode("ascii")
        logo_mime = _image_mime(report_logo_path)
    else:
        LOGGER.warning("Logo not found at %s — report will have no logo", report_logo_path)

    # Feedback v2 #5 — attached "site image" must render in BOTH the
    # in-app preview AND the exported PDF. Previously this was injected
    # post-render only for PDF export, so the image was missing from the
    # preview re-render path and the inline ``<style>`` block was
    # silently dropped by QTextDocument. Now the image flows through the
    # template like the logo, with explicit ``width`` attributes that
    # QTextDocument honors (CSS ``max-width`` is not supported there).
    attached_b64 = ""
    attached_mime = "image/png"
    attached_name = ""
    if attached_image_path:
        img_path = Path(attached_image_path)
        if img_path.exists():
            attached_b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            attached_mime = _image_mime(img_path)
            attached_name = img_path.name

    # Feedback v2 #2 — per-profile operator-prep summary (bar lengths
    # × counts + totals) renders above each profile's cut table. Driven
    # by the shared `aggregate_prep` so HTML / Excel / CSV / in-app
    # purchase table never drift.
    from .bar_aggregation import aggregate_prep, filter_result

    result = filter_result(result, scope)
    prep_by_key: dict[tuple[str, str], object] = {}
    for prep in aggregate_prep(result, scope=None):
        prep_by_key[(prep.profile.strip().lower(), (prep.material or "").strip().lower())] = prep

    html = template.render(
        config=cfg,
        labels=labels,
        tokens=tokens,
        result=result,
        prep_by_key=prep_by_key,
        logo_b64=logo_b64,
        logo_mime=logo_mime,
        attached_image_b64=attached_b64,
        attached_image_mime=attached_mime,
        attached_image_name=attached_name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        project_name=project_name,
        milestone=milestone,
    )

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    return html


def _image_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        return "image/svg+xml"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".bmp":
        return "image/bmp"
    return "image/png"

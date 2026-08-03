"""Report preview widget with allowlisted bar reorder support.

M5 composition: ``ReportPreviewWidget`` now stacks:

* a :class:`ReportFilterBar` (profile chips),
* the original :class:`QTextBrowser` (re-rendered on filter change),
* an :class:`InsightSidebar` (heuristic suggestions + unfit pieces).

The previous public API is preserved — ``set_html``, ``set_image``,
``clear``, ``set_report_context``, and the ``bar_move_requested`` and
``preview_error`` signals all behave as before. New API:

* ``set_nest_result(result)`` — populates filter chips, the insight
  sidebar, and re-renders the HTML when the filter changes.
* ``action_requested(action_id, context)`` — re-emitted from the
  sidebar so callers (the presenter) can wire heuristic actions.
"""

from __future__ import annotations

import base64
from copy import copy
from html import escape
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from tekla_common.design_system import set_accessibility, set_ui_property
from tekla_common.i18n import tr

from ..models import NestResult
from ..services.insights import suggest
from .report_actions import ReportActionError, parse_reorder_url
from .widgets.insight_sidebar import InsightSidebar
from .widgets.report_filter_bar import ReportFilterBar


class ReportPreviewWidget(QWidget):
    """Renders the HTML cut-plan report alongside chips and insights.

    Emits ``bar_move_requested(profile_index, bar_row, direction)`` when
    the user clicks a ▲/▼ reorder link inside the report.  Direction is
    -1 (up) or +1 (down).
    """

    bar_move_requested = Signal(int, int, int)
    preview_error = Signal(str)
    action_requested = Signal(str, dict)
    insight_visibility_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._bar_counts: list[int] | None = None
        self._full_result: NestResult | None = None
        self._raw_html: str = ""
        self._insights_visible: bool = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # Top strip: filter chips on the left, insight toggle pinned right.
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self._filter_bar = ReportFilterBar()
        self._filter_bar.profile_selected.connect(self._on_filter_changed)
        top_row.addWidget(self._filter_bar, stretch=1)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setObjectName("insightToggle")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        set_ui_property(self._toggle_btn, "role", "ghost")
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        top_row.addWidget(self._toggle_btn)
        outer.addLayout(top_row)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(4)
        outer.addLayout(body, stretch=1)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        set_accessibility(
            self._browser,
            "Report preview",
            "Cut-plan report preview with validated reorder links.",
        )
        body.addWidget(self._browser, stretch=1)

        self._sidebar = InsightSidebar()
        self._sidebar.action_requested.connect(self.action_requested.emit)
        body.addWidget(self._sidebar)

        self._refresh_toggle_label()

    # ── Public API ────────────────────────────────────────────

    def set_report_context(self, result: NestResult) -> None:
        """Set valid profile/bar ranges and refresh chips + insights."""
        self._bar_counts = [len(profile.bars) for profile in result.profiles]
        self._full_result = result
        self._filter_bar.set_profiles([p.profile for p in result.profiles])
        self._sidebar.set_insights(suggest(result))

    def set_html(self, html: str) -> None:
        """Display the given HTML content."""
        self._raw_html = html
        self._browser.setHtml(html)

    def set_image(self, path: str) -> bool:
        """Embed an image (e.g. rendered Tekla screenshot) into the report."""
        img_path = Path(path)
        if not img_path.exists():
            self.preview_error.emit(f"Report image not found: {img_path}")
            return False
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        suffix = img_path.suffix.lstrip(".").lower()
        mime = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "bmp": "bmp",
            "gif": "gif",
        }.get(suffix, "png")
        img_tag = self._image_block(b64, mime, img_path.name)
        current = self._browser.toHtml()
        if "</body>" in current.lower():
            idx = current.lower().rfind("</body>")
            new_html = current[:idx] + img_tag + current[idx:]
            self._browser.setHtml(new_html)
            return True
        self._browser.setHtml(
            "<html><body>"
            "<style>"
            ".report-image-wrap{text-align:right;margin:12px 0;}"
            ".report-image{max-width:60%;border:1px solid #8a94a6;}"
            "</style>"
            f"{img_tag}</body></html>"
        )
        return True

    def clear(self) -> None:
        """Clear the preview, including sidebar and chips."""
        self._browser.clear()
        self._bar_counts = None
        self._full_result = None
        self._raw_html = ""
        self._sidebar.set_insights([])
        self._filter_bar.set_profiles([])

    def set_insights_visible(self, visible: bool) -> None:
        """Show or hide the insights sidebar. Persists toggle state."""
        visible = bool(visible)
        self._insights_visible = visible
        self._sidebar.setVisible(visible)
        if self._toggle_btn.isChecked() != visible:
            self._toggle_btn.setChecked(visible)
        self._refresh_toggle_label()
        self.insight_visibility_changed.emit(visible)

    def insights_visible(self) -> bool:
        return self._insights_visible

    def retranslate(self) -> None:
        """Refresh translatable strings (label + tooltip + a11y)."""
        self._refresh_toggle_label()
        if hasattr(self._sidebar, "retranslate"):
            self._sidebar.retranslate()

    def _on_toggle_clicked(self, checked: bool) -> None:
        self.set_insights_visible(checked)

    def _refresh_toggle_label(self) -> None:
        showing = self._toggle_btn.isChecked()
        key = "insights.toggle.hide" if showing else "insights.toggle.show"
        text = tr(key)
        self._toggle_btn.setText(text)
        self._toggle_btn.setToolTip(text)
        set_accessibility(self._toggle_btn, text, text)

    def filtered_result(self) -> NestResult | None:
        """Return the current ``NestResult`` narrowed by the profile chip."""
        if self._full_result is None:
            return None
        current = self._filter_bar.current()
        if not current:
            return self._full_result
        narrowed = copy(self._full_result)
        narrowed.profiles = [p for p in self._full_result.profiles if p.profile == current]
        return narrowed

    # ── Internals ─────────────────────────────────────────────

    def _on_filter_changed(self, _profile: str) -> None:
        # We don't re-render from a template here — that would require
        # importing the report service (an engine boundary).  Instead we
        # ask the presenter for a re-render via ``action_requested``;
        # ``report_filter_changed`` is a dedicated action_id.
        result = self.filtered_result()
        if result is not None:
            self.action_requested.emit(
                "report_filter_changed",
                {"profile": self._filter_bar.current()},
            )
            self._sidebar.set_insights(suggest(result))

    def _on_anchor_clicked(self, url: QUrl) -> None:
        if url.scheme() != "reorder":
            self.preview_error.emit("Unsupported report link.")
            return
        try:
            command = parse_reorder_url(url, self._bar_counts)
        except ReportActionError as exc:
            self.preview_error.emit(str(exc))
            return
        self.bar_move_requested.emit(
            command.profile_index,
            command.bar_row,
            command.direction,
        )

    @staticmethod
    def _image_block(encoded_image: str, mime: str, filename: str) -> str:
        safe_filename = escape(filename)
        return (
            '<div class="report-image-wrap" '
            'style="text-align:right; margin:12px 0; page-break-inside:avoid;">'
            f'<img class="report-image" alt="Report image {safe_filename}" '
            f'src="data:image/{mime};base64,{encoded_image}" '
            'style="max-width:60%; border:1px solid #8a94a6;"/>'
            "</div>"
        )

from __future__ import annotations

import pytest
from PySide6.QtCore import QUrl

from tekla_nest.views.report_actions import ReportActionError, parse_reorder_url


def test_parse_reorder_url_accepts_expected_report_link():
    command = parse_reorder_url(QUrl("reorder:///0/1/-1"), [3])

    assert command.profile_index == 0
    assert command.bar_row == 1
    assert command.direction == -1
    assert command.new_row == 0


def test_parse_reorder_url_accepts_host_style_link():
    command = parse_reorder_url(QUrl("reorder://0/1/1"), [3])

    assert command.profile_index == 0
    assert command.bar_row == 1
    assert command.direction == 1


@pytest.mark.parametrize(
    ("url", "bar_counts"),
    [
        ("https://example.test", [3]),
        ("reorder:///0/1", [3]),
        ("reorder:///0/a/1", [3]),
        ("reorder:///0/1/2", [3]),
        ("reorder:///1/0/1", [3]),
        ("reorder:///0/0/-1", [3]),
    ],
)
def test_parse_reorder_url_rejects_malformed_or_stale_links(url, bar_counts):
    with pytest.raises(ReportActionError):
        parse_reorder_url(QUrl(url), bar_counts)

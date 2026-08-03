from __future__ import annotations

from pathlib import Path


def test_views_do_not_use_widget_local_stylesheets():
    view_root = Path("src/tekla_nest/views")
    offenders = []
    for path in view_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if ".setStyleSheet(" in text:
            offenders.append(str(path))

    assert offenders == []

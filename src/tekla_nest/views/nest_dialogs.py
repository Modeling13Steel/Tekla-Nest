"""File-dialog helpers extracted from ``nest_window.py`` in M2.

Each helper opens a single ``QFileDialog`` and delegates to the presenter.
Returning a small ``(ok, path)`` tuple where useful keeps the call sites
in ``NestWindow`` tiny.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..services.bar_aggregation import available_scope_keys


def _ask_export_scope(parent: QWidget, presenter):
    """Show a scope picker; return ``None`` (all) or a frozenset of keys.

    Returns the sentinel ``False`` if the user cancelled the dialog.
    Skipped (returns ``None``) when there are fewer than 2 profiles.
    """
    result = getattr(presenter, "_last_result", None)
    if result is None:
        return None
    keys = available_scope_keys(result)
    if len(keys) < 2:
        return None  # nothing to choose from — fall through to "all"

    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("dialogs.export_scope.title"))
    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel(tr("dialogs.export_scope.prompt")))
    boxes: list[tuple[QCheckBox, tuple[str, str]]] = []
    for prof, mat in keys:
        label = f"{prof}" + (f" · {mat}" if mat else "")
        cb = QCheckBox(label, dlg)
        cb.setChecked(True)  # default: all selected
        layout.addWidget(cb)
        boxes.append((cb, (prof, mat)))
    bb = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dlg,
    )
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    layout.addWidget(bb)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    selected = [(p, m) for cb, (p, m) in boxes if cb.isChecked()]
    if not selected:
        QMessageBox.warning(
            parent,
            tr("dialogs.export_scope.title"),
            tr("dialogs.export_scope.empty_warn"),
        )
        return False
    if len(selected) == len(keys):
        return None  # all picked → no filter
    return frozenset((p.strip().lower(), m.strip().lower()) for p, m in selected)


def prompt_load_parts_csv(parent: QWidget, presenter) -> None:
    path, _ = QFileDialog.getOpenFileName(
        parent, tr("dialogs.files.select_parts_csv"), "", tr("dialogs.files.csv_filter")
    )
    if path:
        presenter.load_parts_from_csv(path)


def prompt_load_stock_csv(parent: QWidget, presenter) -> None:
    path, _ = QFileDialog.getOpenFileName(
        parent, tr("dialogs.files.select_stock_csv"), "", tr("dialogs.files.csv_filter")
    )
    if path:
        presenter.load_client_stock_csv(path)


def prompt_load_image(parent: QWidget) -> str:
    """Return the picked image path, or empty string if cancelled."""
    path, _ = QFileDialog.getOpenFileName(
        parent, tr("dialogs.files.select_image"), "", tr("dialogs.files.image_filter")
    )
    return path


def _ask_scope_and_milestone(
    parent: QWidget, presenter, purchase_toggle: bool = False
) -> tuple[object, str, bool, bool]:
    """Combined scope + milestone dialog for PDF/Excel export.

    Returns ``(scope, milestone, cancelled, purchase_only)``.

    Profile checkboxes appear when >= 2 profiles are available;
    ``purchase_toggle`` adds the "purchase list only" tickbox (Excel).
    With one profile and no tickbox, only a milestone ``QInputDialog``
    is shown.
    """
    result = getattr(presenter, "_last_result", None)
    keys = available_scope_keys(result) if result is not None else []

    if len(keys) < 2 and not purchase_toggle:
        milestone, ok = QInputDialog.getText(
            parent,
            tr("dialogs.milestone.title"),
            tr("dialogs.milestone.label"),
            text=presenter.milestone,
        )
        if not ok:
            return None, "", True, False
        return None, milestone, False, False

    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("dialogs.export_scope.title"))
    layout = QVBoxLayout(dlg)
    boxes: list[tuple[QCheckBox, tuple[str, str]]] = []
    if len(keys) >= 2:
        layout.addWidget(QLabel(tr("dialogs.export_scope.prompt")))
        for prof, mat in keys:
            cb_label = f"{prof}" + (f" · {mat}" if mat else "")
            cb = QCheckBox(cb_label, dlg)
            cb.setChecked(True)
            layout.addWidget(cb)
            boxes.append((cb, (prof, mat)))
        layout.addWidget(QLabel(""))  # visual spacer

    layout.addWidget(QLabel(tr("dialogs.milestone.label")))
    milestone_edit = QLineEdit(presenter.milestone, dlg)
    layout.addWidget(milestone_edit)

    purchase_cb = None
    if purchase_toggle:
        purchase_cb = QCheckBox(tr("dialogs.export_scope.purchase_only"), dlg)
        purchase_cb.setObjectName("purchaseOnlyCheck")
        layout.addWidget(purchase_cb)

    bb = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dlg,
    )
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    layout.addWidget(bb)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None, "", True, False

    scope = None
    if boxes:
        selected = [(p, m) for cb, (p, m) in boxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(
                parent,
                tr("dialogs.export_scope.title"),
                tr("dialogs.export_scope.empty_warn"),
            )
            return None, "", True, False
        if len(selected) != len(keys):
            scope = frozenset((p.strip().lower(), m.strip().lower()) for p, m in selected)
    purchase_only = purchase_cb is not None and purchase_cb.isChecked()
    return scope, milestone_edit.text(), False, purchase_only


def prompt_export_pdf(parent: QWidget, presenter) -> str:
    """Return the saved path on success or empty string otherwise."""
    scope, milestone, cancelled, _ = _ask_scope_and_milestone(parent, presenter)
    if cancelled:
        return ""
    presenter.milestone = milestone
    path, _ = QFileDialog.getSaveFileName(
        parent, tr("dialogs.files.export_pdf"), "", tr("dialogs.files.pdf_filter")
    )
    if not path or not presenter.export_pdf(path, scope=scope):
        return ""
    QMessageBox.information(
        parent, tr("dialogs.messages.export_title"),
        tr("dialogs.messages.pdf_saved", path=path),
    )
    return path


def prompt_export_excel(parent: QWidget, presenter) -> str:
    scope, milestone, cancelled, purchase_only = _ask_scope_and_milestone(
        parent, presenter, purchase_toggle=True
    )
    if cancelled:
        return ""
    presenter.milestone = milestone
    path, _ = QFileDialog.getSaveFileName(
        parent, tr("dialogs.files.export_excel"), "", tr("dialogs.files.excel_filter")
    )
    if not path or not presenter.export_excel(path, scope=scope, purchase_only=purchase_only):
        return ""
    QMessageBox.information(
        parent, tr("dialogs.messages.export_title"),
        tr("dialogs.messages.excel_saved", path=path),
    )
    return path


def prompt_export_csv(parent: QWidget, presenter) -> str:
    scope = _ask_export_scope(parent, presenter)
    if scope is False:
        return ""
    path, _ = QFileDialog.getSaveFileName(
        parent, tr("dialogs.files.export_csv"), "", tr("dialogs.files.csv_filter")
    )
    if not path or not presenter.export_csv(path, scope=scope):
        return ""
    QMessageBox.information(
        parent, tr("dialogs.messages.export_title"),
        tr("dialogs.messages.csv_saved", path=path),
    )
    return path

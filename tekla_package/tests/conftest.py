"""Shared, headless-safe test configuration for the whole suite.

Under an offscreen Qt platform (CI / no display), a modal ``.exec()`` blocks
forever — notably the close-guard ``QMessageBox`` that pytest-qt triggers when it
tears down a top-level window. We stub the blocking modal calls so the suite runs
headless. No test asserts on an instance ``.exec()`` return value, so this is safe.
"""

from PySide6.QtWidgets import QDialog, QMessageBox

# QMessageBox instances (close guard, CSV error modal, etc.)
QMessageBox.exec = lambda self, *a, **k: QMessageBox.StandardButton.Cancel  # type: ignore[assignment]
QMessageBox.exec_ = QMessageBox.exec  # type: ignore[assignment]

# Generic dialogs (activation, create-license, colour picker, etc.)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected  # type: ignore[assignment]
QDialog.exec_ = QDialog.exec  # type: ignore[assignment]

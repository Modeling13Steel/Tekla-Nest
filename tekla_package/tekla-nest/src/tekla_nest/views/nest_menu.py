"""MenuBuilder — encapsulates the NestWindow menu construction.

Extracted in M2 to keep ``nest_window.py`` within its LOC budget. The
builder owns no state; it returns the action / menu / language-action
dictionaries that ``NestWindow`` keeps on ``self``.

The shape of every entry is unchanged from v2.0 — keys, shortcuts, callback
contracts all match. Tests that introspect ``self._actions`` keep working.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QMenu
from tekla_common.design_system import CommandDescriptor, apply_action_descriptor
from tekla_common.design_system.tokens import Theme
from tekla_common.i18n import available_languages, current_language, tr


@dataclass(frozen=True)
class _Cmd:
    command_id: str
    slot_name: str  # attribute on NestWindow to wire to
    shortcut: str = ""


_FILE_CMDS: tuple[_Cmd, ...] = (
    _Cmd("load_tekla", "_pres.load_parts_from_provider"),
    _Cmd("load_parts_csv", "_on_load_parts_csv", "Ctrl+O"),
    _Cmd("clear_parts", "_on_clear_parts", "Ctrl+Shift+Z"),
)
_FILE_IMAGE_CMDS: tuple[_Cmd, ...] = (_Cmd("load_image", "_on_load_image"),)
_FILE_EXPORT_CMDS: tuple[_Cmd, ...] = (
    _Cmd("export_pdf", "_on_export_pdf"),
    _Cmd("export_excel", "_on_export_excel"),
    _Cmd("export_csv", "_on_export_csv"),
)
_STOCK_CMDS: tuple[_Cmd, ...] = (
    _Cmd("auto_stock", "_on_auto_stock"),
    _Cmd("load_stock_csv", "_on_load_stock_csv"),
)
_NEST_CMDS: tuple[_Cmd, ...] = (_Cmd("calculate", "_on_calculate", "Ctrl+R"),)
_VIEW_CMDS: tuple[_Cmd, ...] = (_Cmd("color_schema", "_on_color_schema"),)


def _resolve_slot(window: QMainWindow, path: str) -> Callable[..., object]:
    """Walk a dotted attribute path on ``window`` to get the bound slot."""
    obj: object = window
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj  # type: ignore[return-value]


def _descriptor(command_id: str, shortcut: str = "") -> CommandDescriptor:
    return CommandDescriptor(
        command_id=command_id,
        text=tr(f"commands.{command_id}.text"),
        status_tip=tr(f"commands.{command_id}.status"),
        shortcut=shortcut,
        toolbar_text=tr(f"commands.{command_id}.toolbar"),
    )


@dataclass
class MenuBuildResult:
    actions: dict[str, QAction]
    menus: dict[str, QMenu]
    language_actions: dict[str, QAction]
    theme_actions: dict[Theme, QAction]
    reduced_motion_action: QAction | None = None


_THEME_ORDER: tuple[Theme, ...] = (Theme.SYSTEM, Theme.LIGHT, Theme.DARK)


class MenuBuilder:
    """Builds the menu bar, language submenu, and bookkeeping dicts."""

    def __init__(
        self,
        window: QMainWindow,
        on_language_change: Callable[[str], None],
        on_theme_change: Callable[[Theme], None] | None = None,
        current_theme: Theme = Theme.LIGHT,
        on_reduced_motion_change: Callable[[bool], None] | None = None,
        reduced_motion_enabled: bool = False,
    ):
        self._window = window
        self._on_language_change = on_language_change
        self._on_theme_change = on_theme_change
        self._current_theme = current_theme
        self._on_reduced_motion_change = on_reduced_motion_change
        self._reduced_motion_enabled = reduced_motion_enabled

    def build(self) -> MenuBuildResult:
        actions: dict[str, QAction] = {}
        menus: dict[str, QMenu] = {}
        bar = self._window.menuBar()

        file_menu = bar.addMenu("")
        menus["file"] = file_menu
        self._add_group(file_menu, _FILE_CMDS, actions)
        file_menu.addSeparator()
        self._add_group(file_menu, _FILE_IMAGE_CMDS, actions)
        file_menu.addSeparator()
        self._add_group(file_menu, _FILE_EXPORT_CMDS, actions)

        stock_menu = bar.addMenu("")
        menus["stock"] = stock_menu
        self._add_group(stock_menu, _STOCK_CMDS, actions)

        nest_menu = bar.addMenu("")
        menus["nesting"] = nest_menu
        self._add_group(nest_menu, _NEST_CMDS, actions)

        view_menu = bar.addMenu("")
        menus["view"] = view_menu
        self._add_group(view_menu, _VIEW_CMDS, actions)

        language_actions = self._build_language_menu(view_menu, menus)

        prefs_menu = bar.addMenu("")
        menus["preferences"] = prefs_menu
        theme_actions = self._build_theme_menu(prefs_menu, menus)
        prefs_menu.addSeparator()
        reduced_motion_action = self._build_reduced_motion_action(prefs_menu)

        return MenuBuildResult(
            actions=actions,
            menus=menus,
            language_actions=language_actions,
            theme_actions=theme_actions,
            reduced_motion_action=reduced_motion_action,
        )

    # ------------------------------------------------------------------
    def _add_group(
        self, menu: QMenu, commands: tuple[_Cmd, ...], actions: dict[str, QAction]
    ) -> None:
        for cmd in commands:
            action = QAction(self._window)
            apply_action_descriptor(action, _descriptor(cmd.command_id, cmd.shortcut))
            action.triggered.connect(_resolve_slot(self._window, cmd.slot_name))
            menu.addAction(action)
            actions[cmd.command_id] = action

    def _build_language_menu(self, view_menu: QMenu, menus: dict[str, QMenu]) -> dict[str, QAction]:
        language_menu = view_menu.addMenu("")
        menus["language"] = language_menu
        group = QActionGroup(self._window)
        group.setExclusive(True)
        language_actions: dict[str, QAction] = {}
        for code, name in available_languages().items():
            action = QAction(name, self._window)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(code == current_language())
            action.triggered.connect(
                lambda _checked=False, lang=code: self._on_language_change(lang)
            )
            group.addAction(action)
            language_menu.addAction(action)
            language_actions[code] = action
        return language_actions

    def _build_theme_menu(self, prefs_menu: QMenu, menus: dict[str, QMenu]) -> dict[Theme, QAction]:
        theme_menu = prefs_menu.addMenu("")
        menus["theme"] = theme_menu
        group = QActionGroup(self._window)
        group.setExclusive(True)
        theme_actions: dict[Theme, QAction] = {}
        for theme in _THEME_ORDER:
            action = QAction(tr(f"theme.{theme.value}"), self._window)
            action.setCheckable(True)
            action.setData(theme.value)
            action.setObjectName(f"themeAction_{theme.value}")
            action.setChecked(theme == self._current_theme)
            handler = self._on_theme_change
            if handler is not None:
                action.triggered.connect(lambda _checked=False, t=theme, h=handler: h(t))
            group.addAction(action)
            theme_menu.addAction(action)
            theme_actions[theme] = action
        return theme_actions

    def _build_reduced_motion_action(self, prefs_menu: QMenu) -> QAction:
        action = QAction(tr("preferences.reduced_motion"), self._window)
        action.setCheckable(True)
        action.setObjectName("reducedMotionAction")
        action.setChecked(self._reduced_motion_enabled)
        handler = self._on_reduced_motion_change
        if handler is not None:
            action.toggled.connect(lambda checked, h=handler: h(bool(checked)))
        prefs_menu.addAction(action)
        return action


def retranslate_window(window) -> None:
    """Re-apply translations to all menus, actions and child widgets."""
    from tekla_common.config.app_config import get_config
    from tekla_common.i18n import available_languages, current_language, tr

    cfg = get_config()
    window.setWindowTitle(cfg.title)
    menus = window._menus
    for key, i18n_key in (
        ("file", "menus.file"),
        ("stock", "menus.stock"),
        ("nesting", "menus.nesting"),
        ("view", "menus.view"),
        ("language", "menus.language"),
        ("preferences", "menus.preferences"),
        ("theme", "menus.theme"),
    ):
        if key in menus:
            menus[key].setTitle(tr(i18n_key))
    for theme, action in window._theme_actions.items():
        action.setText(tr(f"theme.{theme.value}"))
    if window._reduced_motion_action is not None:
        window._reduced_motion_action.setText(tr("preferences.reduced_motion"))
    for code, action in window._language_actions.items():
        action.setText(available_languages()[code])
        action.setChecked(code == current_language())
    retranslate_actions(window._actions)
    window._chrome.retranslate()
    window._chrome.set_languages(available_languages(), current_language())
    window._kpi_strip.retranslate()
    window._status.retranslate()
    window._parts_table.retranslate()
    window._stock_tabs.retranslate()
    if hasattr(window, "_purchase_table"):
        window._purchase_table.retranslate()
        window._result_tabs.setTabText(0, tr("report_tab"))
        window._result_tabs.setTabText(1, tr("purchase.tab"))
    if hasattr(window, "_report_preview"):
        window._report_preview.retranslate()
    if window._status.level == "ready":
        window._status.set_status(tr("status.ready"), "ready")
    window._sync_action_state()


def retranslate_actions(actions: dict[str, QAction]) -> None:
    """Re-apply translated descriptors to every action after language change."""
    for command_id, action in actions.items():
        shortcut = action.shortcut().toString()
        apply_action_descriptor(action, _descriptor(command_id, shortcut))

"""Menuconfig behaviour, delegated to kconfiglib's own menuconfig.py.

Rendering text, node visibility, value strings, info text, validation and
search all come from the unmodified upstream module. Only the curses UI state
(current menu, selection) is ported here so a different front-end can drive it.
"""

import errno
import os
import re
from collections.abc import Callable, Sequence
from typing import Any

from kconfiglib import (
    HEX,
    INT,
    MENU,
    STRING,
    TRI_TO_STR,
    TYPE_TO_STR,
    Choice,
    KconfigError,
    Symbol,
    standard_config_filename,
    standard_sc_expr_str,
)

from kcon_ui.upstream import mc as _mc

MAIN_HELP_LINES: list[str] = _mc._MAIN_HELP_LINES
JUMP_TO_HELP_LINES: list[str] = _mc._JUMP_TO_HELP_LINES
INFO_HELP_LINES: list[str] = _mc._INFO_HELP_LINES

# kconfiglib is untyped; its Kconfig, MenuNode, Symbol and Choice objects are Any here.
Node = Any
Kconf = Any
SaveFunction = Callable[[str], str]
PAGE_END = 10**6


def describe_os_error(error: OSError, fallback_filename: str) -> str:
    name = errno.errorcode.get(error.errno, str(error.errno)) if error.errno else "unknown"
    reason = error.strerror or str(error)
    if error.filename in (None, fallback_filename):
        return f"{reason} (errno: {name})"
    return f"{reason} (errno: {name}, file: {error.filename})"


class EmptyConfigurationError(Exception):
    """Nothing in the Kconfig tree can be shown or configured."""


class _ErrorCollector:
    """Captures upstream _error() calls so the UI can show them itself."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def __call__(self, text: str) -> None:
        self.messages.append(text)


class MenuconfigEngine:
    def __init__(self, kconf: Kconf) -> None:
        self.kconf = kconf
        self.conf_filename = standard_config_filename()
        self.minconf_filename = "defconfig"
        self.show_help = False
        self._errors = _ErrorCollector()
        _mc._kconf = kconf
        _mc._error = self._errors
        _mc._sorted_sc_nodes.__defaults__[0].clear()
        _mc._sorted_menu_comment_nodes.__defaults__[0].clear()
        _mc._show_name = False
        _mc._show_all = False
        _mc._conf_filename = self.conf_filename

        self.load_message = kconf.load_config()
        self.conf_changed = not os.path.exists(self.conf_filename) or _mc._needs_save()
        self._start_in_show_all_if_empty()
        kconf.warn = False

        self.cur_menu = kconf.top_node
        self.shown = self.shown_nodes(self.cur_menu)
        self.sel = 0

    def _start_in_show_all_if_empty(self) -> None:
        if self.shown_nodes(self.kconf.top_node):
            return
        self.show_all = True
        if not self.shown_nodes(self.kconf.top_node):
            raise EmptyConfigurationError(
                "Empty configuration -- nothing to configure. "
                "Check that environment variables are set properly."
            )

    # ---- modes ---------------------------------------------------------
    @property
    def show_all(self) -> bool:
        return bool(_mc._show_all)

    @show_all.setter
    def show_all(self, value: bool) -> None:
        _mc._show_all = value

    @property
    def show_name(self) -> bool:
        return bool(_mc._show_name)

    @show_name.setter
    def show_name(self, value: bool) -> None:
        _mc._show_name = value

    def toggle_show_name(self) -> None:
        self.show_name = not self.show_name

    def toggle_show_help(self) -> None:
        self.show_help = not self.show_help

    def active_modes(self) -> list[str]:
        modes: list[str] = []
        if self.show_help:
            modes.append("show-help (toggle with [F])")
        if self.show_name:
            modes.append("show-name")
        if self.show_all:
            modes.append("show-all")
        return modes

    # ---- text ----------------------------------------------------------
    def shown_nodes(self, menu: Node) -> list[Node]:
        nodes: list[Node] = _mc._shown_nodes(menu)
        return nodes

    def node_text(self, node: Node) -> str:
        return str(_mc._node_str(node))

    def is_visible(self, node: Node) -> bool:
        return bool(_mc._visible(node))

    def info_text(self, node: Node) -> str:
        return str(_mc._info_str(node))

    def help_text(self, node: Node) -> str:
        if isinstance(node.item, (Symbol, Choice)) and node.help:
            return str(node.help)
        return "(no help)"

    def menu_path(self) -> list[str]:
        prompts: list[str] = []
        menu = self.cur_menu
        while menu is not self.kconf.top_node:
            prompts.append(menu.prompt[0] if menu.prompt else standard_sc_expr_str(menu.item))
            menu = menu.parent
        prompts.append("(Top)")
        return prompts[::-1]

    @property
    def title(self) -> str:
        return str(self.kconf.mainmenu_text)

    @property
    def selected_node(self) -> Node:
        return self.shown[self.sel]

    # ---- navigation ----------------------------------------------------
    def select_delta(self, delta: int) -> None:
        self.sel = max(0, min(len(self.shown) - 1, self.sel + delta))

    def enter(self, menu: Node) -> bool:
        if not menu.is_menuconfig:
            return False
        shown_sub = self.shown_nodes(menu)
        if not shown_sub:
            return False
        self.cur_menu = menu
        self.shown = shown_sub
        self.sel = 0
        if isinstance(menu.item, Choice):
            self._select_selected_choice_sym()
        return True

    def leave(self) -> None:
        if self.cur_menu is self.kconf.top_node:
            return
        parent = _mc._parent_menu(self.cur_menu)
        self.shown = self.shown_nodes(parent)
        self.sel = self.shown.index(self.cur_menu)
        self.cur_menu = parent

    def at_top(self) -> bool:
        return self.cur_menu is self.kconf.top_node

    def jump_to(self, node: Node) -> None:
        old_show_all = self.show_all
        jump_into = (isinstance(node.item, Choice) or node.item == MENU) and node.list
        if jump_into:
            self.cur_menu = node
            node = node.list
        else:
            self.cur_menu = _mc._parent_menu(node)
        self.shown = self.shown_nodes(self.cur_menu)
        if node not in self.shown:
            self.show_all = True
            self.shown = self.shown_nodes(self.cur_menu)
        self.sel = self.shown.index(node)
        if jump_into and not old_show_all and self.show_all:
            self.toggle_show_all()
        if jump_into and isinstance(self.cur_menu.item, Choice):
            self._select_selected_choice_sym()

    def toggle_show_all(self) -> None:
        self.show_all = not self.show_all
        new_shown = self.shown_nodes(self.cur_menu)
        new_sel = self._closest_surviving_index(new_shown)
        if new_sel is None:
            self.show_all = True
            return
        self.shown = new_shown
        self.sel = new_sel

    def _closest_surviving_index(self, new_shown: list[Node]) -> int | None:
        for node in self.shown[self.sel :: -1]:
            if node in new_shown:
                return new_shown.index(node)
        for node in self.shown[self.sel + 1 :]:
            if node in new_shown:
                return new_shown.index(node)
        return None

    def _select_selected_choice_sym(self) -> None:
        choice = self.cur_menu.item
        if not choice.selection:
            return
        for node in choice.selection.nodes:
            if node in self.shown:
                self.sel = self.shown.index(node)
                return

    def refresh_menu(self) -> None:
        sel_node = self.shown[self.sel]
        self.shown = self.shown_nodes(self.cur_menu)
        if sel_node in self.shown:
            self.sel = self.shown.index(sel_node)
        else:
            self.sel = min(self.sel, len(self.shown) - 1)

    # ---- editing -------------------------------------------------------
    def is_changeable(self, node: Node) -> bool:
        return bool(_mc._changeable(node))

    def needs_text_input(self, node: Node) -> bool:
        return self.is_changeable(node) and node.item.orig_type in (INT, HEX, STRING)

    def input_title(self, node: Node) -> str:
        sc = node.item
        return f"{node.prompt[0]} ({TYPE_TO_STR[sc.orig_type]})"

    def input_info(self, node: Node) -> str | None:
        info = _mc._range_info(node.item)
        return None if info is None else str(info)

    def validate(self, node: Node, text: str) -> tuple[str, str | None]:
        """Returns (normalised text, error message or None)."""
        sc = node.item
        if sc.orig_type in (INT, HEX):
            text = text.strip()
            if sc.orig_type == HEX and not text.startswith(("0x", "0X")):
                text = "0x" + text
        self._errors.messages.clear()
        if _mc._check_valid(sc, text):
            return text, None
        return text, self._errors.messages[-1]

    def set_value(self, sc: Node, val: Any) -> None:
        if val in TRI_TO_STR:
            val = TRI_TO_STR[val]
        if val != sc.str_value:
            sc.set_value(val)
            self.conf_changed = True
            self.refresh_menu()

    def cycle_value(self, node: Node) -> bool:
        """Toggle a bool/tristate/choice symbol. False if not changeable."""
        if not self.is_changeable(node):
            return False
        sc = node.item
        if len(sc.assignable) == 1:
            self.set_value(sc, sc.assignable[0])
        else:
            index = sc.assignable.index(sc.tri_value)
            self.set_value(sc, sc.assignable[(index + 1) % len(sc.assignable)])
        self._leave_after_y_choice(node)
        return True

    def _leave_after_y_choice(self, node: Node) -> None:
        if _mc._is_y_mode_choice_sym(node.item) and not node.list:
            self.leave()

    def press_space(self) -> bool:
        """Space: toggle if possible, else enter. True if text input is needed."""
        node = self.selected_node
        if self.needs_text_input(node):
            return True
        if not self.cycle_value(node):
            self.enter(node)
        return False

    def press_enter(self) -> bool:
        """Enter: enter if possible, else change. True if text input is needed."""
        node = self.selected_node
        if self.enter(node):
            return False
        if self.needs_text_input(node):
            return True
        self.cycle_value(node)
        return False

    def commit_text(self, node: Node, text: str) -> tuple[str, str | None]:
        """Validates and applies typed text. Returns (normalised text, error)."""
        text, error = self.validate(node, text)
        if error is None:
            self.set_value(node.item, text)
        return text, error

    def set_selected_tri(self, tri_val: int) -> None:
        sc = self.selected_node.item
        if isinstance(sc, (Symbol, Choice)) and tri_val in sc.assignable:
            self.set_value(sc, tri_val)

    # ---- search --------------------------------------------------------
    def search(self, text: str) -> tuple[list[Node], str | None]:
        """Returns (matching nodes, regex error or None); same rules as upstream."""
        try:
            searches = [re.compile(r).search for r in text.lower().split()]
        except re.error as e:
            message = "Bad regular expression"
            if hasattr(e, "msg"):
                message += ": " + e.msg
            return [], message
        matches = [n for n in _mc._sorted_sc_nodes() if self._sc_matches(n, searches)]
        matches += [
            n
            for n in _mc._sorted_menu_comment_nodes()
            if all(s(n.prompt[0].lower()) for s in searches)
        ]
        return matches, None

    @staticmethod
    def _sc_matches(node: Node, searches: Sequence[Callable[[str], Any]]) -> bool:
        sc = node.item
        for search in searches:
            name_hit = sc.name and search(sc.name.lower())
            prompt_hit = node.prompt and search(node.prompt[0].lower())
            if not (name_hit or prompt_hit):
                return False
        return True

    # ---- load / save ---------------------------------------------------
    def load(self, filename: str) -> str | None:
        """Returns an error message, or None on success."""
        filename = os.path.expanduser(filename)
        try:
            self.kconf.load_config(filename)
        except (OSError, ValueError, KconfigError) as error:
            return f"Error loading '{filename}'\n\n{self._describe_error(error, filename)}"
        self.conf_filename = filename
        self.conf_changed = bool(_mc._needs_save())
        if self.selected_node not in self.shown_nodes(self.cur_menu):
            self.show_all = True
        self.refresh_menu()
        return None

    def save_config(self, filename: str) -> tuple[str | None, str | None]:
        return self._save(self.kconf.write_config, filename, "configuration")

    def save_min_config(self, filename: str) -> tuple[str | None, str | None]:
        return self._save(self.kconf.write_min_config, filename, "minimal configuration")

    def _save(
        self, save_fn: SaveFunction, filename: str, description: str
    ) -> tuple[str | None, str | None]:
        """Returns (success message, error message)."""
        filename = os.path.expanduser(filename)
        try:
            return str(save_fn(filename)), None
        except (OSError, ValueError, KconfigError) as error:
            reason = self._describe_error(error, filename)
            return None, f"Error saving {description} to '{filename}'\n\n{reason}"

    @staticmethod
    def _describe_error(error: Exception, filename: str) -> str:
        if isinstance(error, OSError):
            return describe_os_error(error, filename)
        return str(error)

    def save_dialog_info(self) -> str:
        return str(_mc._load_save_info())

"""Single access point for kconfiglib's menuconfig module.

kcon-ui reuses private helpers of upstream's menuconfig.py. This module
imports it (with a curses stand-in) and verifies that every helper kcon-ui
depends on is present, so an incompatible kconfiglib fails loudly at start-up
instead of misbehaving later.
"""

from types import ModuleType
from typing import Any

from kcon_ui.curses_stub import install_curses_stub

install_curses_stub()

import menuconfig as _menuconfig  # noqa: E402

REQUIRED_NAMES = (
    "_INFO_HELP_LINES",
    "_JUMP_TO_HELP_LINES",
    "_MAIN_HELP_LINES",
    "_NAMED_COLORS",
    "_STYLES",
    "_changeable",
    "_check_valid",
    "_info_str",
    "_is_y_mode_choice_sym",
    "_load_save_info",
    "_needs_save",
    "_node_str",
    "_parent_menu",
    "_range_info",
    "_shown_nodes",
    "_sorted_menu_comment_nodes",
    "_sorted_sc_nodes",
    "_visible",
)


class UpstreamIncompatibleError(ImportError):
    """The installed kconfiglib does not provide what kcon-ui needs."""


def _missing_names(module: ModuleType) -> list[str]:
    return [name for name in REQUIRED_NAMES if not hasattr(module, name)]


def _verify(module: ModuleType) -> ModuleType:
    missing = _missing_names(module)
    if missing:
        raise UpstreamIncompatibleError(
            "The installed kconfiglib is not compatible with kcon-ui "
            "(missing in menuconfig.py: {}). Install a supported version: "
            "pip install 'kconfiglib>=14.1.0,<15'".format(", ".join(missing))
        )
    return module


mc: Any = _verify(_menuconfig)

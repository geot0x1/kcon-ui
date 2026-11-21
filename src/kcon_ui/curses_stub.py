"""Lets kconfiglib's unmodified menuconfig.py be imported without curses.

menuconfig.py only needs `curses` at import time and in its own drawing
code. All of that is bypassed here: only its curses-free logic is used. The
colour constants are real so upstream's named-colour table stays correct.
"""

import sys
import types

_COLORS = {
    "COLOR_BLACK": 0,
    "COLOR_RED": 1,
    "COLOR_GREEN": 2,
    "COLOR_YELLOW": 3,
    "COLOR_BLUE": 4,
    "COLOR_MAGENTA": 5,
    "COLOR_CYAN": 6,
    "COLOR_WHITE": 7,
}


def install_curses_stub() -> None:
    if "curses" in sys.modules:
        return
    stub = types.ModuleType("curses")
    stub.__dict__.update(_COLORS)
    stub.__dict__["__getattr__"] = lambda name: 0
    sys.modules["curses"] = stub

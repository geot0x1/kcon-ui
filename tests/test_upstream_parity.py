"""Drives upstream's own menuconfig.py and kcon-ui's engine with identical random
key sequences and checks that every visible state matches.

The reference is a separate import of the unmodified upstream module, so its
globals do not interfere with the engine under test.
"""

import importlib.util
import os
import random
import sys

import pytest
from kconfiglib import Kconfig

from kcon_ui.curses_stub import install_curses_stub
from kcon_ui.engine import MenuconfigEngine

SAMPLE = """\
mainmenu "Parity"

config MODULES
    bool "Modules"
    option modules

config FOO
    bool "Foo"
    default y

config BAR
    bool "Bar (implicit submenu child)"
    depends on FOO

config BAZ
    tristate "Baz"
    depends on MODULES
    default m

menuconfig NET
    bool "Networking"

if NET

config NET_SPEED
    int "Speed"
    range 1 100
    default 10

config NET_ADDR
    hex "Address"
    default 0x10

config NET_NAME
    string "Name"
    default "eth0"

endif

menu "Hardware"

choice
    prompt "Board"
    default BOARD_A

config BOARD_A
    bool "Board A"

config BOARD_B
    bool "Board B"

config BOARD_C
    bool "Board C"
    depends on FOO

endchoice

comment "Misc"

config HIDDEN_PARENT
    bool
    default y

config HIDDEN_CHILD
    bool "Child of hidden parent"
    depends on HIDDEN_PARENT && !FOO

endmenu

menu "Conditional menu"
    visible if BAR

config INSIDE
    bool "Inside"

endmenu
"""

TEXT_CANDIDATES = ["1", "0x10", "abc", "", "99999", "50", "ff"]


class _FakeWindow:
    def getmaxyx(self):
        return (30, 100)


def _load_reference():
    install_curses_stub()
    import menuconfig

    spec = importlib.util.spec_from_file_location("menuconfig_ref", menuconfig.__file__)
    module = importlib.util.module_from_spec(spec)
    sys.modules["menuconfig_ref"] = module
    spec.loader.exec_module(module)
    return module


class _Reference:
    """Upstream's navigation, driven the way its main loop drives it."""

    def __init__(self, kconf) -> None:
        self.m = m = _load_reference()
        m._kconf = kconf
        m._conf_filename = m.standard_config_filename()
        m._conf_changed = m._load_config()
        m._show_all = False
        m._show_name = False
        m._cur_menu = kconf.top_node
        m._shown = m._shown_nodes(m._cur_menu)
        m._sel_node_i = 0
        m._menu_scroll = 0
        m._parent_screen_rows = []
        m._menu_win = _FakeWindow()
        m._error = lambda text: None
        self.pending_text = None
        m._input_dialog = self._input_dialog

    def _input_dialog(self, title, initial, info):
        text, self.pending_text = self.pending_text, None
        return text

    def snapshot(self):
        m = self.m
        return (
            [m._node_str(n) for n in m._shown],
            m._sel_node_i,
            m._show_all,
            m._show_name,
            m._conf_changed,
            self._path(),
            _values(m._kconf),
        )

    def _path(self):
        m = self.m
        prompts, menu = [], m._cur_menu
        while menu is not m._kconf.top_node:
            prompts.append(menu.prompt[0] if menu.prompt else m.standard_sc_expr_str(menu.item))
            menu = menu.parent
        return ["(Top)", *prompts[::-1]]

    def search_all(self):
        return self.m._sorted_sc_nodes() + self.m._sorted_menu_comment_nodes()


def _values(kconf):
    return {s.name: s.str_value for s in kconf.unique_defined_syms}


def _engine_snapshot(engine):
    return (
        [engine.node_text(n) for n in engine.shown],
        engine.sel,
        engine.show_all,
        engine.show_name,
        engine.conf_changed,
        engine.menu_path(),
        _values(engine.kconf),
    )


def _apply(op, arg, ref, engine):
    m = ref.m
    if op == "down":
        m._select_next_menu_entry()
        engine.select_delta(1)
    elif op == "up":
        m._select_prev_menu_entry()
        engine.select_delta(-1)
    elif op == "last":
        m._select_last_menu_entry()
        engine.select_delta(10**6)
    elif op == "first":
        m._select_first_menu_entry()
        engine.select_delta(-(10**6))
    elif op == "space":
        node = m._shown[m._sel_node_i]
        if not m._change_node(node):
            m._enter_menu(node)
        _engine_space(engine, arg)
    elif op == "enter":
        node = m._shown[m._sel_node_i]
        if not m._enter_menu(node):
            m._change_node(node)
        _engine_enter(engine, arg)
    elif op in ("y", "n", "m"):
        tri = {"n": 0, "m": 1, "y": 2}[op]
        m._set_sel_node_tri_val(tri)
        engine.set_selected_tri(tri)
    elif op == "leave":
        m._leave_menu()
        engine.leave()
    elif op == "all":
        m._toggle_show_all()
        engine.toggle_show_all()
    elif op == "name":
        m._show_name = not m._show_name
        engine.toggle_show_name()
    elif op == "jump":
        nodes = ref.search_all()
        if nodes:
            target = nodes[arg % len(nodes)]
            m._jump_to(target)
            matches, _ = engine.search("")
            engine.jump_to(matches[arg % len(matches)])


def _engine_space(engine, text):
    if engine.press_space():
        engine.commit_text(engine.selected_node, text)


def _engine_enter(engine, text):
    if engine.press_enter():
        engine.commit_text(engine.selected_node, text)


OPS = [
    "down",
    "up",
    "down",
    "up",
    "space",
    "enter",
    "enter",
    "y",
    "n",
    "m",
    "leave",
    "all",
    "name",
    "jump",
    "last",
    "first",
]


def _run_sequence(kconfig_path, seed, steps, monkeypatch, tmp_path):
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / "parity.config"))
    ref = _Reference(Kconfig(kconfig_path, warn=False))
    engine = MenuconfigEngine(Kconfig(kconfig_path, warn=False))
    rng = random.Random(seed)
    history = []
    for _ in range(steps):
        op = rng.choice(OPS)
        text = rng.choice(TEXT_CANDIDATES)
        arg = rng.randrange(10**6) if op == "jump" else text
        ref.pending_text = text
        history.append((op, arg))
        _apply(op, arg, ref, engine)
        assert _engine_snapshot(engine) == ref.snapshot(), (seed, history[-12:])


@pytest.mark.parametrize("seed", range(40))
def test_sample_kconfig_matches_upstream(seed, tmp_path, monkeypatch):
    kconfig = tmp_path / "Kconfig"
    kconfig.write_text(SAMPLE)
    _run_sequence(str(kconfig), seed, 250, monkeypatch, tmp_path)


@pytest.mark.skipif(
    "KCON_PARITY_KCONFIG" not in os.environ,
    reason="set KCON_PARITY_KCONFIG to a real Kconfig to run against it",
)
@pytest.mark.parametrize("seed", range(10))
def test_real_kconfig_matches_upstream(seed, tmp_path, monkeypatch):
    _run_sequence(os.environ["KCON_PARITY_KCONFIG"], seed, 400, monkeypatch, tmp_path)

import pytest
from kconfiglib import Kconfig

from kcon_ui.app import MenuconfigApp
from kcon_ui.engine import MenuconfigEngine

KCONFIG = """\
mainmenu "Test"

config FOO
    bool "Enable foo"
    default y

config BAR
    bool "Bar"
    depends on FOO

config NUM
    int "Number"
    range 1 10
    default 5

menu "Sub"

choice
    prompt "Pick"
    default OPT_A

config OPT_A
    bool "A"

config OPT_B
    bool "B"

endchoice

endmenu
"""


@pytest.fixture
def engine(tmp_path, monkeypatch):
    kconfig = tmp_path / "Kconfig"
    kconfig.write_text(KCONFIG)
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / ".config"))
    return MenuconfigEngine(Kconfig(str(kconfig)))


def test_toggle_hides_dependents(engine):
    def names():
        return [engine.node_text(n) for n in engine.shown]

    assert any("Bar" in t for t in names())
    engine.cycle_value(engine.shown[0])
    assert not any("Bar" in t for t in names())
    assert engine.conf_changed


def test_int_validation_uses_range(engine):
    node = engine.shown[2]
    assert engine.needs_text_input(node)
    assert engine.validate(node, "11")[1] is not None
    assert engine.validate(node, "3") == ("3", None)


def test_choice_enter_and_leave(engine):
    sub = next(n for n in engine.shown if "Sub" in engine.node_text(n))
    assert engine.enter(sub)
    assert engine.menu_path() == ["(Top)", "Sub"]
    engine.leave()
    assert engine.at_top()


def test_search_and_jump(engine):
    matches, error = engine.search("opt_b")
    assert error is None and len(matches) == 1
    engine.jump_to(matches[0])
    assert engine.selected_node is matches[0]


def test_bad_regex_reported(engine):
    assert engine.search("(")[1].startswith("Bad regular expression")


def test_save_writes_config(engine, tmp_path):
    _message, error = engine.save_config(str(tmp_path / "out.config"))
    assert error is None
    assert "CONFIG_FOO=y" in (tmp_path / "out.config").read_text()


async def test_ui_space_toggles_and_quit(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("space")
        assert engine.kconf.syms["FOO"].str_value == "n"
        await pilot.press("a")
        assert engine.show_all
        await pilot.press("q")
        await pilot.press("n")
    assert "not saved" in app.return_value

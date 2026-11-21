import pytest
from kconfiglib import Kconfig

from kcon_ui.app import MenuconfigApp, MenuList
from kcon_ui.engine import MenuconfigEngine
from kcon_ui.styles import load_styles
from tests.test_upstream_parity import SAMPLE


@pytest.fixture
def engine(tmp_path, monkeypatch):
    kconfig = tmp_path / "Kconfig"
    kconfig.write_text(SAMPLE)
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / ".config"))
    return MenuconfigEngine(Kconfig(str(kconfig), warn=False))


async def test_uppercase_keys_match_lowercase(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("J")
        assert engine.sel == 1
        await pilot.press("K")
        assert engine.sel == 0
        await pilot.press("A")
        assert engine.show_all
        await pilot.press("C")
        assert engine.show_name
        await pilot.press("F")
        assert engine.show_help


@pytest.mark.parametrize("key", ["left", "backspace", "h", "H"])
async def test_left_at_top_does_not_quit(engine, key):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press(key)
        assert app.is_running
        assert not app.screen_stack[1:]


async def test_escape_at_top_opens_quit_prompt(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert len(app.screen_stack) == 2
        await pilot.press("c")
        assert len(app.screen_stack) == 1


async def test_enter_text_symbol_validates_range(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        net = next(i for i, n in enumerate(engine.shown) if "Networking" in engine.node_text(n))
        app.query_one(MenuList).highlighted = net
        await pilot.press("space")
        await pilot.press("enter")
        await pilot.press("enter")
        await pilot.press(*"999", "enter")
        await pilot.press("enter")
        assert engine.kconf.syms["NET_SPEED"].str_value == "10"
        await pilot.press("escape")
        await pilot.press(*"42", "enter")


async def test_info_screen_keys_close(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        for key in ["escape", "q", "Q", "h", "H", "left", "backspace"]:
            await pilot.press("question_mark")
            assert len(app.screen_stack) == 2
            await pilot.press(key)
            assert len(app.screen_stack) == 1, key


async def test_jump_from_info_slash(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        await pilot.press("slash")
        await pilot.press(*"board_b", "enter")
        assert "Board B" in engine.node_text(engine.selected_node)


def test_default_style_matches_upstream_default():
    styles = load_styles({})
    assert styles["list"].fg == "#000000"
    assert styles["list"].bg == "#c0c0c0"
    assert styles["help"] == styles["path"]


def test_menuconfig_style_env_overrides():
    styles = load_styles({"MENUCONFIG_STYLE": "aquatic selection=fg:#ff0000,bg:black"})
    assert styles["selection"].fg == "#ff0000"
    assert styles["path"].bg == styles["body"].bg
    assert styles["frame"].bg != load_styles({})["frame"].bg


async def test_style_applied_to_selection(engine):
    env = {"MENUCONFIG_STYLE": "selection=fg:#00ff00,bg:#0000ff"}
    app = MenuconfigApp(engine, env)
    async with app.run_test():
        assert "#00ff00" in app.CSS and "#0000ff" in app.CSS

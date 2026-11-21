"""End-to-end dialog flows driven through the real Textual app."""

import pytest
from kconfiglib import Kconfig
from textual.widgets import Input

from kcon_ui.app import MenuconfigApp
from kcon_ui.engine import MenuconfigEngine
from tests.test_upstream_parity import SAMPLE


@pytest.fixture
def paths(tmp_path, monkeypatch):
    kconfig = tmp_path / "Kconfig"
    kconfig.write_text(SAMPLE)
    config = tmp_path / ".config"
    monkeypatch.setenv("KCONFIG_CONFIG", str(config))
    return kconfig, config


@pytest.fixture
def engine(paths):
    return MenuconfigEngine(Kconfig(str(paths[0]), warn=False))


def _set_input(app, text):
    app.screen.query_one(Input).value = str(text)


async def _type(pilot, text):
    await pilot.press(*text)


async def test_save_flow_writes_file_and_clears_changed(engine, paths):
    _, config = paths
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("space")
        assert engine.conf_changed
        await pilot.press("s")
        _set_input(app, config)
        await pilot.press("enter")
        await pilot.press("enter")
        assert not engine.conf_changed
    assert config.exists()
    assert "CONFIG_FOO" in config.read_text()


async def test_save_error_reopens_input(engine, tmp_path):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("s")
        _set_input(app, tmp_path / "missing_dir" / "x")
        await pilot.press("enter")
        await pilot.press("enter")
        assert len(app.screen_stack) == 2
        await pilot.press("escape")
        assert len(app.screen_stack) == 1


async def test_save_minimal_config(engine, tmp_path):
    target = tmp_path / "min_config"
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("d")
        _set_input(app, target)
        await pilot.press("enter")
        await pilot.press("enter")
    assert target.exists()
    assert engine.minconf_filename == str(target)


async def test_load_flow_applies_saved_config(engine, tmp_path):
    saved = tmp_path / "other.config"
    saved.write_text("# CONFIG_FOO is not set\n")
    engine.conf_changed = False
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("o")
        _set_input(app, saved)
        await pilot.press("enter")
        await pilot.press("enter")
        assert engine.kconf.syms["FOO"].str_value == "n"


async def test_load_missing_file_shows_error(engine, tmp_path):
    engine.conf_changed = False
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("o")
        _set_input(app, tmp_path / "absent.config")
        await pilot.press("enter")
        assert len(app.screen_stack) == 2
        await pilot.press("enter")


async def test_load_with_unsaved_changes_asks_first(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("space")
        await pilot.press("o")
        await pilot.press("c")
        assert len(app.screen_stack) == 1
        await pilot.press("o")
        await pilot.press("o")
        assert len(app.screen_stack) == 2
        await pilot.press("escape")


async def test_quit_yes_saves_and_exits(engine, paths):
    _, config = paths
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("space")
        await pilot.press("q")
        await pilot.press("y")
    assert config.exists()
    assert app.return_code == 0


async def test_quit_cancel_keeps_running(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("space")
        await pilot.press("q")
        await pilot.press("c")
        assert app.is_running


async def test_quit_without_changes_exits_immediately(engine, paths):
    _, config = paths
    config.write_text("")
    engine.conf_changed = False
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("q")
    assert "No changes" in app.return_value


async def test_ctrl_c_aborts_with_code_130(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+c")
    assert app.return_code == 130


async def test_jump_dialog_navigation_keys(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("slash")
        for key in ("down", "up", "pagedown", "pageup", "end", "home", "ctrl+d"):
            await pilot.press(key)
        await pilot.press("ctrl+f")
        assert len(app.screen_stack) == 3
        await pilot.press("escape")
        await pilot.press("escape")
        assert len(app.screen_stack) == 1


async def test_jump_bad_regex_does_not_crash(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await _type(pilot, "(")
        await pilot.press("enter")
        assert len(app.screen_stack) == 2
        await pilot.press("escape")


async def test_info_scroll_keys(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        for key in (
            "j",
            "k",
            "J",
            "K",
            "down",
            "up",
            "pagedown",
            "pageup",
            "end",
            "home",
            "G",
            "g",
        ):
            await pilot.press(key)
        await pilot.press("escape")
        assert len(app.screen_stack) == 1


async def test_show_all_marks_hidden_rows_and_restyles_on_move(engine):
    app = MenuconfigApp(engine)
    async with app.run_test() as pilot:
        await pilot.press("a")
        for _ in range(len(engine.shown)):
            await pilot.press("j")
        assert engine.sel == len(engine.shown) - 1

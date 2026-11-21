"""Failure handling: bad input files, unwritable paths, unsupported environments."""

import io
import sys

import pytest
from kconfiglib import Kconfig

from kcon_ui import __main__ as cli
from kcon_ui import upstream
from kcon_ui.engine import EmptyConfigurationError, MenuconfigEngine, describe_os_error
from tests.test_upstream_parity import SAMPLE


@pytest.fixture
def kconfig_file(tmp_path, monkeypatch):
    path = tmp_path / "Kconfig"
    path.write_text(SAMPLE)
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / ".config"))
    return path


@pytest.fixture
def engine(kconfig_file):
    return MenuconfigEngine(Kconfig(str(kconfig_file), warn=False))


def test_load_missing_file_reports_error(engine, tmp_path):
    error = engine.load(str(tmp_path / "missing.config"))
    assert error is not None and "missing.config" in error
    assert not engine.conf_changed or engine.conf_filename != str(tmp_path / "missing.config")


def test_load_invalid_encoding_reports_error_instead_of_crashing(engine, tmp_path):
    bad = tmp_path / "bad.config"
    bad.write_bytes(b"CONFIG_FOO=\xff\xfe\n# \x80\x81\n")
    result = engine.load(str(bad))
    assert result is None or "bad.config" in result


def test_save_to_unwritable_path_reports_error(engine, tmp_path):
    target = tmp_path / "no_such_dir" / "out.config"
    message, error = engine.save_config(str(target))
    assert message is None
    assert error is not None and "out.config" in error


def test_save_minimal_config_roundtrip(engine, tmp_path):
    target = tmp_path / "defconfig"
    message, error = engine.save_min_config(str(target))
    assert error is None and message
    assert target.exists()


def test_refresh_menu_survives_vanishing_selection(engine):
    engine.sel = len(engine.shown) - 1
    engine.shown = engine.shown + engine.shown[:0]
    engine.shown_nodes = lambda menu: engine.shown[:1]
    engine.refresh_menu()
    assert engine.sel == 0


def test_empty_kconfig_raises_dedicated_error(tmp_path, monkeypatch):
    path = tmp_path / "Kconfig"
    path.write_text('mainmenu "Empty"\n')
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / ".config"))
    with pytest.raises(EmptyConfigurationError):
        MenuconfigEngine(Kconfig(str(path), warn=False))


def test_describe_os_error_handles_missing_fields():
    assert "unknown" in describe_os_error(OSError("boom"), "x")
    error = FileNotFoundError(2, "No such file", "other.txt")
    assert "other.txt" in describe_os_error(error, "x")


def test_upstream_guard_lists_missing_helpers():
    class Fake:
        pass

    with pytest.raises(upstream.UpstreamIncompatibleError, match="_node_str"):
        upstream._verify(Fake())


def test_upstream_guard_accepts_installed_kconfiglib():
    assert upstream._missing_names(upstream.mc) == []


# ---- command line --------------------------------------------------------
def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0
    assert "kcon-ui" in capsys.readouterr().out


def test_cli_requires_terminal(monkeypatch, capsys, kconfig_file):
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    assert cli.main([str(kconfig_file)]) == cli.EXIT_USAGE
    assert "interactive terminal" in capsys.readouterr().err


def test_cli_missing_kconfig(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "_is_interactive", lambda: True)
    assert cli.main([str(tmp_path / "nope")]) == cli.EXIT_ERROR
    assert "kcon-ui: error:" in capsys.readouterr().err


def test_cli_syntax_error_in_kconfig(monkeypatch, capsys, tmp_path):
    path = tmp_path / "Kconfig"
    path.write_text("config\n  this is not valid\n")
    monkeypatch.setattr(cli, "_is_interactive", lambda: True)
    assert cli.main([str(path)]) == cli.EXIT_ERROR
    assert "kcon-ui: error:" in capsys.readouterr().err


def test_cli_empty_configuration(monkeypatch, capsys, tmp_path):
    path = tmp_path / "Kconfig"
    path.write_text('mainmenu "Empty"\n')
    monkeypatch.setenv("KCONFIG_CONFIG", str(tmp_path / ".config"))
    monkeypatch.setattr(cli, "_is_interactive", lambda: True)
    assert cli.main([str(path)]) == cli.EXIT_ERROR
    assert "nothing to configure" in capsys.readouterr().err


def test_cli_runs_app_and_returns_its_code(monkeypatch, capsys, kconfig_file):
    class FakeApp:
        return_code = 130

        def __init__(self, engine):
            self.engine = engine

        def run(self):
            return "bye"

    monkeypatch.setattr(cli, "_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "MenuconfigApp", FakeApp)
    assert cli.main([str(kconfig_file)]) == 130
    assert "bye" in capsys.readouterr().out

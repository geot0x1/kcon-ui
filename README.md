# kcon-ui

**A drop-in replacement for kconfiglib's `menuconfig`, built with [Textual](https://textual.textualize.io/).**

`menuconfig` is the terminal interface used to configure projects that describe
their options in `Kconfig` files (Linux, Zephyr, and many embedded firmware
projects). On Windows it needs the `windows-curses` package, which has no
wheels for newer Python versions, so it often cannot be installed. kcon-ui does
the same job without curses, on any platform Textual supports.

## What it does

kcon-ui opens your `Kconfig` file as an interactive menu tree. You can browse
menus, turn options on and off, edit numbers and strings, search for a symbol,
read its help and dependencies, and save the result to a `.config` file.

It reads and writes exactly the same files as `menuconfig`, so you can use the
two interchangeably on the same project.

## How it stays compatible with menuconfig

kcon-ui does not re-implement Kconfig behaviour. kconfiglib's own
`menuconfig.py` is imported unmodified, with a small stand-in for the `curses`
module. These all come straight from upstream and behave identically:

- which entries are visible, including implicit submenus and `menuconfig` symbols
- how each line is drawn (`[*]`, `<M>`, `(X)`, `(NEW)`, `--->`, `*** comment ***`)
- the symbol information screen (type, value, help, dependencies, defaults,
  `select`/`imply`, where it is defined)
- int/hex range checking and hex `0x` handling
- search rules (regular expressions, several terms, symbols, choices, menus, comments)
- loading, saving and saving a minimal config (`defconfig`)
- the colour schemes, including `MENUCONFIG_STYLE`

Only the Textual screen and the menu navigation state (current menu, selected
row) are written here. A test (`tests/test_upstream_parity.py`) drives upstream's
own `menuconfig.py` and kcon-ui's engine with the same random key sequences and
checks that every screen state matches.

Inputs also match menuconfig:

- the Kconfig file is the first argument (default `Kconfig`)
- the config file comes from `$KCONFIG_CONFIG` (default `.config`)
- `$srctree` and the other kconfiglib environment variables work as usual
- `MENUCONFIG_STYLE` customises colours, for example
  `MENUCONFIG_STYLE="aquatic selection=fg:white,bg:red"`

## Keys

Same as menuconfig. Letter keys work in upper and lower case.

| Key | Action |
|---|---|
| Space | toggle the option, or enter the menu |
| Enter / Right / l | enter the menu, or change the option |
| Esc | leave the menu (asks to save when at the top level) |
| Left / Backspace / h | leave the menu |
| y / n / m | set the option to yes / no / module |
| j k g G, Up Down Home End | move |
| PgUp PgDn, Ctrl-U Ctrl-D | move by 6 rows |
| s | save the configuration |
| d | save a minimal configuration |
| o | load a configuration |
| / | jump to a symbol (Ctrl-F shows its info, Enter jumps) |
| ? | show information about the selected item |
| f | show-help mode: show the help text of the selected item at the bottom |
| c | show-name mode: show the `CONFIG_` names |
| a | show-all mode: also show hidden options |
| q | quit (asks to save if there are changes) |
| Ctrl-C | abort without saving |

## Install

    pip install kcon-ui                 # once published to an index
    pip install path\to\kcon_ui-0.1.0-py3-none-any.whl

Requires Python 3.10 or newer. Dependencies (`textual`, `kconfiglib`) are
installed automatically.

## Use

Run it from the directory that holds your `Kconfig`:

    kcon-ui                  # uses ./Kconfig and ./.config
    kcon-ui path\to\Kconfig
    set KCONFIG_CONFIG=build\.config
    kcon-ui

You can also run it as `python -m kcon_ui`. `kcon-ui --version` prints the version.

Exit codes: `0` normal exit, `1` the Kconfig or config file could not be read
(or there is nothing to configure), `2` not run in an interactive terminal,
`130` aborted with Ctrl-C.

## Develop

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e .[dev]
    ruff check src tests && ruff format --check src tests
    mypy
    pytest --cov
    python -m build                     # writes dist\*.whl and dist\*.tar.gz

See [CONTRIBUTING.md](CONTRIBUTING.md) for the design rules, and
[CHANGELOG.md](CHANGELOG.md) for release notes.

To run the comparison against upstream on a real project as well:

    set KCON_PARITY_KCONFIG=path\to\Kconfig
    pytest tests\test_upstream_parity.py

Layout:

| File | Role |
|---|---|
| `curses_stub.py` | lets upstream's `menuconfig.py` import without curses |
| `engine.py` | menuconfig behaviour: visibility, editing, search, load/save, navigation |
| `styles.py` | `MENUCONFIG_STYLE` parsing, turned into Textual styles |
| `app.py` | the main menu screen and its key bindings |
| `screens.py` | dialogs: input, yes/no keys, symbol info, jump-to |
| `__main__.py` | command-line entry point |

## Not included

- The curses-only `monochrome` style (used by upstream when a terminal has no
  colours). Textual always renders in colour.
- Mouse-specific behaviour. Clicking selects a row, but menuconfig has no mouse
  support to match.

## License

MIT. See [LICENSE](LICENSE).

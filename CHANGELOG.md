# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-21

### Added

- Textual-based menuconfig for Kconfig projects, driven by kconfiglib's own
  `menuconfig.py` so visibility, value strings, info text, validation, search,
  load and save behave exactly like upstream.
- Menuconfig key bindings (upper and lower case), jump-to-symbol search,
  symbol information screen, and the show-help, show-name and show-all modes.
- `MENUCONFIG_STYLE` support with upstream's default and `aquatic` schemes.
- `kcon-ui` command and `python -m kcon_ui`, with `--version`, clear error
  messages and meaningful exit codes (0 ok, 1 error, 2 usage, 130 aborted).
- Start-up check that the installed kconfiglib provides every helper used.
- Differential test suite comparing every screen state with upstream's own
  `menuconfig.py` across randomised key sequences.

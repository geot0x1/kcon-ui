# Contributing

Thanks for helping improve kcon-ui.

## Set up

    python -m venv .venv
    .venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
    pip install -e ".[dev]"
    pre-commit install

## Before you open a pull request

All of these must pass; CI runs the same checks on Linux, Windows and macOS.

    ruff check src tests
    ruff format --check src tests
    mypy
    pytest --cov

## Design rules

- **Match upstream.** Behaviour that menuconfig already defines must come from
  kconfiglib's `menuconfig.py` (through `kcon_ui/upstream.py`), not be
  re-implemented. Only rendering and navigation state live in this package.
- **No curses.** Nothing may import `curses` directly.
- **Fail with a message, not a traceback.** User-facing failures (bad files,
  unwritable paths, incompatible environments) must be reported cleanly.
- **Add tests with every change.** Behavioural changes to navigation or editing
  must keep `tests/test_upstream_parity.py` passing. To run it against your
  own project's Kconfig:

      set KCON_PARITY_KCONFIG=path\to\Kconfig
      pytest tests\test_upstream_parity.py

## Commits and pull requests

Keep commits focused, explain the why in the message, and update
`CHANGELOG.md` under "Unreleased".

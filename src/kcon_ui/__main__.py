"""Textual menuconfig. Reads the Kconfig file and .config exactly like
kconfiglib's menuconfig: the Kconfig filename is the first argument (default
"Kconfig"), and the configuration file comes from $KCONFIG_CONFIG (default
".config"). Environment variables such as $srctree are honoured."""

import argparse
import sys
from collections.abc import Sequence

from kconfiglib import Kconfig, KconfigError

from kcon_ui import __version__
from kcon_ui.app import MenuconfigApp
from kcon_ui.engine import EmptyConfigurationError, MenuconfigEngine

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kcon-ui",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "kconfig",
        metavar="KCONFIG",
        nargs="?",
        default="Kconfig",
        help="top-level Kconfig file (default: Kconfig)",
    )
    parser.add_argument("--version", action="version", version="kcon-ui " + __version__)
    return parser


def _fail(message: str, code: int) -> int:
    print("kcon-ui: error: " + message, file=sys.stderr)
    return code


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _create_engine(kconfig_path: str) -> MenuconfigEngine:
    return MenuconfigEngine(Kconfig(kconfig_path, warn=False))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not _is_interactive():
        return _fail("an interactive terminal is required", EXIT_USAGE)
    try:
        engine = _create_engine(args.kconfig)
    except (OSError, ValueError, KconfigError, EmptyConfigurationError) as error:
        return _fail(str(error), EXIT_ERROR)
    print(engine.load_message)
    app = MenuconfigApp(engine)
    message = app.run()
    if message:
        print(message)
    return app.return_code or EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

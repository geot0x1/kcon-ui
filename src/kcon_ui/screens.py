"""Modal dialogs for the menuconfig front-end."""

from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from kcon_ui.bindings import both_cases
from kcon_ui.engine import INFO_HELP_LINES, JUMP_TO_HELP_LINES, MenuconfigEngine, Node

PAGE_JUMP = 6


class KeyDialog(ModalScreen[str | None]):
    """Shows text and returns whichever of `keys` was pressed (None on ESC)."""

    DEFAULT_CSS = """
    KeyDialog { align: center middle; }
    KeyDialog > Vertical {
        width: auto; min-width: 40; max-width: 80; height: auto; padding: 1 2;
    }
    """

    def __init__(self, title: str, text: str, keys: str) -> None:
        super().__init__()
        self._title = title
        self._text = text
        self._keys = keys

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog") as box:
            box.border_title = self._title
            yield Static(Text(self._text))

    def on_key(self, event: Key) -> None:
        event.stop()
        if event.key == "escape":
            self.dismiss(None)
            return
        typed = {"enter": "\n", "space": " "}.get(event.key, event.character)
        if typed and typed.lower() in self._keys:
            self.dismiss(typed.lower())


class InputScreen(ModalScreen[str | None]):
    """Single-line text entry. Returns the text, or None on ESC."""

    DEFAULT_CSS = """
    InputScreen { align: center middle; }
    InputScreen > Vertical { width: 70%; min-width: 40; height: auto; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, initial: str, info: str | None) -> None:
        super().__init__()
        self._title = title
        self._initial = initial
        self._info = info

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog") as box:
            box.border_title = self._title
            yield Input(value=self._initial)
            if self._info:
                yield Static(Text("\n" + self._info))

    def on_mount(self) -> None:
        self.query_one(Input).cursor_position = len(self._initial)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class InfoScreen(ModalScreen[str | None]):
    """Full-screen symbol information. Returns "jump" if '/' was pressed."""

    DEFAULT_CSS = """
    InfoScreen #info-title { padding: 0 1; }
    InfoScreen #info-help { padding: 0 1; height: auto; }
    """
    BINDINGS: ClassVar[list[BindingType]] = (
        both_cases("q", "close")
        + both_cases("h", "close")
        + [Binding("escape,left,backspace", "close", show=False)]
        + both_cases("j", "scroll(1)")
        + both_cases("k", "scroll(-1)")
        + [
            Binding("down", "scroll(1)", show=False),
            Binding("up", "scroll(-1)", show=False),
            Binding("pagedown,ctrl+d", f"scroll({PAGE_JUMP})", show=False),
            Binding("pageup,ctrl+u", f"scroll(-{PAGE_JUMP})", show=False),
            Binding("end,G", "scroll(100000)", show=False),
            Binding("home,g", "scroll(-100000)", show=False),
            Binding("slash", "jump", show=False),
        ]
    )

    def __init__(self, engine: MenuconfigEngine, node: Node, from_jump: bool) -> None:
        super().__init__()
        self._engine = engine
        self._node = node
        self._from_jump = from_jump

    def compose(self) -> ComposeResult:
        title = "Information for " + self._engine.node_text(self._node).strip()
        yield Static(Text(title), id="info-title")
        with VerticalScroll(can_focus=False):
            yield Static(Text(self._engine.info_text(self._node)))
        yield Static(Text("\n".join(INFO_HELP_LINES)), id="info-help")

    def action_scroll(self, lines: int) -> None:
        self.query_one(VerticalScroll).scroll_relative(y=lines, animate=False)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_jump(self) -> None:
        self.dismiss(None if self._from_jump else "jump")


class JumpScreen(ModalScreen[Node | None]):
    """Incremental symbol search. Returns the chosen MenuNode, or None."""

    DEFAULT_CSS = """
    JumpScreen #jump-error { color: $error; height: auto; padding: 0 1; }
    JumpScreen OptionList { height: 1fr; }
    JumpScreen #jump-help { padding: 0 1; height: auto; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("down", "cursor('down')", show=False, priority=True),
        Binding("up", "cursor('up')", show=False, priority=True),
        Binding("pagedown,ctrl+d", "page(1)", show=False, priority=True),
        Binding("pageup", "page(-1)", show=False, priority=True),
        Binding("end", "edge('last')", show=False, priority=True),
        Binding("home", "edge('first')", show=False, priority=True),
        Binding("ctrl+f", "info", show=False),
    ]

    def __init__(self, engine: MenuconfigEngine) -> None:
        super().__init__()
        self._engine = engine
        self._matches: list[Node] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Jump to symbol", id="jump-input")
        yield Static("", id="jump-error")
        yield OptionList()
        yield Static(Text("\n".join(JUMP_TO_HELP_LINES)), id="jump-help")

    def on_mount(self) -> None:
        self._refill("")

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refill(event.value)

    def _refill(self, text: str) -> None:
        self._matches, error = self._engine.search(text)
        self.query_one("#jump-error", Static).update(Text(error or ""))
        options = self.query_one(OptionList)
        options.clear_options()
        options.add_options([Option(Text(self._engine.node_text(n))) for n in self._matches])
        if self._matches:
            options.highlighted = 0

    def on_input_submitted(self, event: Input.Submitted) -> None:
        node = self._selected()
        if node is not None:
            self.dismiss(node)

    def _selected(self) -> Node | None:
        index = self.query_one(OptionList).highlighted
        if index is None or index >= len(self._matches):
            return None
        return self._matches[index]

    def _move(self, delta: int) -> None:
        if not self._matches:
            return
        options = self.query_one(OptionList)
        current = options.highlighted or 0
        options.highlighted = max(0, min(len(self._matches) - 1, current + delta))

    def action_cursor(self, direction: str) -> None:
        self._move(1 if direction == "down" else -1)

    def action_page(self, direction: int) -> None:
        self._move(direction * PAGE_JUMP)

    def action_edge(self, which: str) -> None:
        self._move(-100000 if which == "first" else 100000)

    def action_info(self) -> None:
        node = self._selected()
        if node is not None:
            self.app.push_screen(InfoScreen(self._engine, node, True))

    def action_cancel(self) -> None:
        self.dismiss(None)

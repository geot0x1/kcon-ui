"""Textual front-end replicating kconfiglib's menuconfig key bindings."""

import textwrap
from collections.abc import Callable, Mapping
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from kcon_ui.bindings import both_cases
from kcon_ui.engine import MAIN_HELP_LINES, MenuconfigEngine, Node
from kcon_ui.screens import InfoScreen, InputScreen, JumpScreen, KeyDialog
from kcon_ui.styles import build_css, load_styles

PAGE_JUMP = 6


_MENU_BINDINGS: list[BindingType] = [
    Binding("space", "app.toggle_node", show=False),
    Binding("enter,right", "app.enter_node", show=False),
    Binding("escape", "app.escape", show=False),
    Binding("left,backspace", "app.leave_menu", show=False),
    Binding("slash", "app.jump", show=False),
    Binding("question_mark", "app.info", show=False),
    Binding("pagedown,ctrl+d", f"app.move({PAGE_JUMP})", show=False),
    Binding("pageup,ctrl+u", f"app.move(-{PAGE_JUMP})", show=False),
    Binding("end,G", "app.move(100000)", show=False),
    Binding("home,g", "app.move(-100000)", show=False),
    Binding("ctrl+c", "app.abort", show=False, priority=True),
    *both_cases("l", "app.enter_node"),
    *both_cases("h", "app.leave_menu"),
    *both_cases("y", "app.set_tri(2)"),
    *both_cases("m", "app.set_tri(1)"),
    *both_cases("n", "app.set_tri(0)"),
    *both_cases("s", "app.save"),
    *both_cases("d", "app.save_min"),
    *both_cases("o", "app.load"),
    *both_cases("f", "app.toggle_help"),
    *both_cases("c", "app.toggle_name"),
    *both_cases("a", "app.toggle_all"),
    *both_cases("q", "app.quit_dialog"),
    *both_cases("j", "app.move(1)"),
    *both_cases("k", "app.move(-1)"),
]


class MenuList(OptionList):
    BINDINGS: ClassVar[list[BindingType]] = _MENU_BINDINGS


class MenuconfigApp(App[str | None]):
    LAYOUT_CSS = """
    #path { padding: 0 1; }
    #title { text-align: center; }
    #modes { text-align: right; }
    #help { padding: 0 1; height: 8; }
    MenuList { height: 1fr; }
    """

    def __init__(
        self, engine: MenuconfigEngine, environment: Mapping[str, str] | None = None
    ) -> None:
        self._element_styles = load_styles(environment)
        self.CSS = self.LAYOUT_CSS + build_css(self._element_styles)  # type: ignore[misc]
        super().__init__()
        self._engine = engine
        self._rendering = False
        self._marked_index: int | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="path")
        yield Static(Text(self._engine.title), id="title")
        yield MenuList()
        yield Static(id="modes")
        yield Static(id="help")

    def on_mount(self) -> None:
        self.query_one(MenuList).focus()
        self._render()

    # ---- rendering -----------------------------------------------------
    def _render(self) -> None:
        engine = self._engine
        menu_list = self.query_one(MenuList)
        self._rendering = True
        menu_list.clear_options()
        menu_list.add_options([self._option_for(i) for i in range(len(engine.shown))])
        menu_list.highlighted = engine.sel
        self._marked_index = engine.sel
        self._rendering = False
        self._render_chrome()

    def _option_for(self, index: int) -> Option:
        return Option(self._prompt_for(index))

    def _prompt_for(self, index: int) -> Text:
        node = self._engine.shown[index]
        text = self._engine.node_text(node)
        if self._engine.is_visible(node) or not self._engine.show_all:
            return Text(text)
        key = "inv-selection" if index == self._engine.sel else "inv-list"
        return Text(text, style=self._element_styles[key].rich_style())

    def _restyle_selection(self, new_index: int) -> None:
        menu_list = self.query_one(MenuList)
        for index in {self._marked_index, new_index}:
            if index is not None and index < len(self._engine.shown):
                menu_list.replace_option_prompt_at_index(index, self._prompt_for(index))
        self._marked_index = new_index

    def _render_chrome(self) -> None:
        engine = self._engine
        self.query_one("#path", Static).update(Text(" > ".join(engine.menu_path())))
        modes = engine.active_modes()
        text = " and ".join(modes) + " mode enabled" if modes else ""
        self.query_one("#modes", Static).update(Text(text))
        help_bar = self.query_one("#help", Static)
        help_bar.update(Text(self._help_text()))
        help_bar.set_class(engine.show_help, "show-help")

    def _help_text(self) -> str:
        engine = self._engine
        if not engine.show_help:
            return "\n".join(MAIN_HELP_LINES)
        width = max(self.size.width - 2, 20)
        return "\n".join(textwrap.wrap(engine.help_text(engine.selected_node), width))

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if self._rendering or event.option_index is None:
            return
        self._engine.sel = event.option_index
        self._restyle_selection(event.option_index)
        self._render_chrome()

    # ---- navigation actions -------------------------------------------
    def action_move(self, delta: int) -> None:
        self._engine.select_delta(delta)
        self.query_one(MenuList).highlighted = self._engine.sel

    def action_enter_node(self) -> None:
        self._after_press(self._engine.press_enter())

    def action_toggle_node(self) -> None:
        self._after_press(self._engine.press_space())

    def _after_press(self, needs_text: bool) -> None:
        node = self._engine.selected_node
        if needs_text:
            self._edit_text(node, node.item.str_value)
        else:
            self._render()

    def action_leave_menu(self) -> None:
        self._engine.leave()
        self._render()

    def action_escape(self) -> None:
        if self._engine.at_top():
            self.action_quit_dialog()
        else:
            self.action_leave_menu()

    def action_abort(self) -> None:
        self.exit("Aborted (configuration not saved)", return_code=130)

    def action_set_tri(self, value: int) -> None:
        self._engine.set_selected_tri(value)
        self._render()

    def action_toggle_help(self) -> None:
        self._engine.toggle_show_help()
        self._render_chrome()

    def action_toggle_name(self) -> None:
        self._engine.toggle_show_name()
        self._render()

    def action_toggle_all(self) -> None:
        self._engine.toggle_show_all()
        self._render()

    # ---- editing ------------------------------------------------------
    def _edit_text(self, node: Node, initial: str) -> None:
        engine = self._engine

        def done(text: str | None) -> None:
            if text is None:
                return
            text, error = engine.commit_text(node, text)
            if error:
                self._message("Error", error, lambda: self._edit_text(node, text))
                return
            self._render()

        self.push_screen(
            InputScreen(engine.input_title(node), initial, engine.input_info(node)),
            done,
        )

    # ---- info / jump --------------------------------------------------
    def action_info(self) -> None:
        self.push_screen(
            InfoScreen(self._engine, self._engine.selected_node, False), self._after_info
        )

    def _after_info(self, result: str | None) -> None:
        if result == "jump":
            self.action_jump()

    def action_jump(self) -> None:
        def done(node: Node | None) -> None:
            if node is not None:
                self._engine.jump_to(node)
                self._render()

        self.push_screen(JumpScreen(self._engine), done)

    # ---- dialogs ------------------------------------------------------
    def _message(self, title: str, text: str, then: Callable[[], None] | None = None) -> None:
        def done(_result: str | None) -> None:
            if then:
                then()

        self.push_screen(KeyDialog(title, text, " \n"), done)

    def _prompt_filename(
        self,
        description: str,
        default: str,
        save_fn: Callable[[str], tuple[str | None, str | None]],
        on_saved: Callable[[str], None],
    ) -> None:
        engine = self._engine

        def done(filename: str | None) -> None:
            if filename is None:
                return
            message, error = save_fn(filename)
            if error:
                self._message(
                    "Error",
                    error,
                    lambda: self._prompt_filename(description, filename, save_fn, on_saved),
                )
                return
            self._message("Success", message or "")
            on_saved(filename)

        self.push_screen(
            InputScreen(
                f"Filename to save {description} to",
                default,
                engine.save_dialog_info(),
            ),
            done,
        )

    def action_save(self) -> None:
        def saved(filename: str) -> None:
            self._engine.conf_filename = filename
            self._engine.conf_changed = False

        self._prompt_filename(
            "configuration", self._engine.conf_filename, self._engine.save_config, saved
        )

    def action_save_min(self) -> None:
        def saved(filename: str) -> None:
            self._engine.minconf_filename = filename

        self._prompt_filename(
            "minimal configuration",
            self._engine.minconf_filename,
            self._engine.save_min_config,
            saved,
        )

    def action_load(self) -> None:
        engine = self._engine
        if not engine.conf_changed:
            self._prompt_load(engine.conf_filename)
            return

        def confirmed(key: str | None) -> None:
            if key == "o":
                self._prompt_load(engine.conf_filename)

        self.push_screen(
            KeyDialog(
                "Load",
                "You have unsaved changes. Load new\nconfiguration anyway?\n\n"
                "         (O)K  (C)ancel",
                "oc",
            ),
            confirmed,
        )

    def _prompt_load(self, default: str) -> None:
        engine = self._engine

        def done(filename: str | None) -> None:
            if filename is None:
                return
            error = engine.load(filename)
            if error:
                self._message("Error", error, lambda: self._prompt_load(filename))
                return
            self._render()
            self._message("Success", "Loaded " + engine.conf_filename)

        self.push_screen(InputScreen("File to load", default, engine.save_dialog_info()), done)

    def action_quit_dialog(self) -> None:
        engine = self._engine
        if not engine.conf_changed:
            self.exit(f"No changes to save (for '{engine.conf_filename}')")
            return

        def answered(key: str | None) -> None:
            if key == "y":
                message, error = engine.save_config(engine.conf_filename)
                if error:
                    self._message("Error", error)
                else:
                    self.exit(message)
            elif key == "n":
                self.exit(f"Configuration ({engine.conf_filename}) was not saved")

        self.push_screen(
            KeyDialog("Quit", " Save configuration?\n\n(Y)es  (N)o  (C)ancel", "ync"),
            answered,
        )

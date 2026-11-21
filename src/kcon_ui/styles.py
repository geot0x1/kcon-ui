"""MENUCONFIG_STYLE support, using upstream's style templates and colour names."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from rich.color import Color
from rich.style import Style

from kcon_ui.upstream import mc as _mc

_IS_WINDOWS = os.name == "nt"


@dataclass(frozen=True)
class ElementStyle:
    fg: str | None = None
    bg: str | None = None
    bold: bool = False
    underline: bool = False

    def rich_style(self) -> Style:
        return Style(color=self.fg, bgcolor=self.bg, bold=self.bold, underline=self.underline)

    def css(self) -> str:
        parts = []
        if self.fg:
            parts.append(f"color: {self.fg};")
        if self.bg:
            parts.append(f"background: {self.bg};")
        decorations = [n for n, on in (("bold", self.bold), ("underline", self.underline)) if on]
        if decorations:
            parts.append("text-style: {};".format(" ".join(decorations)))
        return " ".join(parts)


def _ansi_hex(number: int) -> str:
    red, green, blue = Color.from_ansi(number).get_truecolor()
    return f"#{red:02x}{green:02x}{blue:02x}"


def _parse_color(definition: str) -> str | None:
    value = definition.split(":", 1)[1]
    if re.match("#[A-Fa-f0-9]{6}", value):
        return value[:7].lower()
    if value in _mc._NAMED_COLORS:
        return _ansi_hex(_mc._NAMED_COLORS[value])
    try:
        number = int(value, 0)
    except ValueError:
        return None
    return _ansi_hex(number) if 0 <= number <= 255 else None


def _parse_definition(definition: str) -> ElementStyle:
    style = ElementStyle()
    for field in definition.split(",") if definition else []:
        if field.startswith("fg:"):
            style = replace(style, fg=_parse_color(field))
        elif field.startswith("bg:"):
            style = replace(style, bg=_parse_color(field))
        elif field == "bold":
            style = replace(style, bold=not _IS_WINDOWS)
        elif field == "standout":
            style = replace(style, fg=style.bg, bg=style.fg)
        elif field == "underline":
            style = replace(style, underline=True)
    return style


def _parse_into(styles: dict[str, ElementStyle], text: str) -> None:
    for word in text.split():
        if "=" in word:
            key, data = word.split("=", 1)
            styles[key] = styles[data] if data in styles else _parse_definition(data)
        elif word in _mc._STYLES:
            _parse_into(styles, _mc._STYLES[word])


def load_styles(environment: Mapping[str, str] | None = None) -> dict[str, ElementStyle]:
    environment = os.environ if environment is None else environment
    styles: dict[str, ElementStyle] = {}
    _parse_into(styles, "default")
    if "MENUCONFIG_STYLE" in environment:
        _parse_into(styles, environment["MENUCONFIG_STYLE"])
    return styles


def build_css(s: dict[str, ElementStyle]) -> str:
    selection = s["selection"].css()
    return """
    Screen {{ {body} }}
    #path {{ {path} }}
    #title, #modes {{ {separator} }}
    #help {{ {help} }}
    #help.show-help {{ {show_help} }}
    MenuList, JumpScreen OptionList {{ {list} }}
    OptionList > .option-list--option-highlighted,
    OptionList:focus > .option-list--option-highlighted {{ {selection} }}
    .dialog {{ {body} border: round {frame_bg}; border-title-color: {frame_fg};
              border-title-background: {frame_bg}; }}
    Input, Input:focus {{ {edit} }}
    #jump-input, #jump-input:focus {{ {jump_edit} }}
    #info-title {{ {separator} }}
    #info-help, #jump-help {{ {help} }}
    InfoScreen VerticalScroll {{ {text} }}
    """.format(
        body=s["body"].css(),
        path=s["path"].css(),
        separator=s["separator"].css(),
        help=s["help"].css(),
        show_help=s["show-help"].css(),
        list=s["list"].css(),
        selection=selection,
        frame_bg=s["frame"].bg or "white",
        frame_fg=s["frame"].fg or "black",
        edit=s["edit"].css(),
        jump_edit=s["jump-edit"].css(),
        text=s["text"].css(),
    )

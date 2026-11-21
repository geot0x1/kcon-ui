import pytest

from kcon_ui.styles import ElementStyle, build_css, load_styles


def _style(definition):
    return load_styles({"MENUCONFIG_STYLE": "list=" + definition})["list"]


def test_named_numeric_and_rgb_colours():
    assert _style("fg:red").fg == "#800000"
    assert _style("fg:9").fg is not None
    assert _style("fg:#102030,bg:#abcdef") == ElementStyle(fg="#102030", bg="#abcdef")


@pytest.mark.parametrize("bad", ["fg:nonsense", "fg:999", "fg:-1", "bg:"])
def test_invalid_colours_are_ignored(bad):
    channel = bad[:2]
    assert getattr(_style(bad), channel) is None


def test_attributes_and_unknown_attribute():
    style = _style("underline,wobble")
    assert style.underline


def test_standout_swaps_colours():
    style = _style("fg:#111111,bg:#222222,standout")
    assert (style.fg, style.bg) == ("#222222", "#111111")


def test_template_reference_and_unknown_template():
    styles = load_styles({"MENUCONFIG_STYLE": "aquatic nonexistent text=path"})
    assert styles["text"] == styles["path"]


def test_css_contains_every_element_and_is_valid_for_textual():
    css = build_css(load_styles({}))
    for selector in ("#path", "#help.show-help", "MenuList", ".dialog", "#jump-input"):
        assert selector in css


def test_element_style_renders_rich_and_css():
    style = ElementStyle(fg="#112233", bg="#445566", bold=True, underline=True)
    assert style.rich_style().bold
    assert "text-style: bold underline" in style.css()
    assert ElementStyle().css() == ""

"""Key-binding helpers shared by the screens."""

from textual.binding import Binding, BindingType


def both_cases(keys: str, action: str) -> list[BindingType]:
    """Binds every letter in `keys` in lower and upper case, like menuconfig."""
    return [Binding(k, action, show=False) for key in keys for k in (key.lower(), key.upper())]

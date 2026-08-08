"""Progress reporting shared by the fetching and downloading steps."""

from __future__ import annotations

from collections.abc import Callable

# Called with a single human readable line describing what is happening now.
ProgressCallback = Callable[[str], None]


def noop_progress(_message: str) -> None:
    """Discard a progress message.

    Args:
        _message (str): The message to discard.
    """


__all__ = ("ProgressCallback", "noop_progress")

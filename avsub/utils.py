"""General utilities."""

import functools
import os


def separate(f):
    """Draw a horizontal line before and after the given function."""

    @functools.wraps(f)
    def w(*args, **kw) -> None:
        print('-' * os.get_terminal_size().columns)
        f(*args, **kw)
        print('-' * os.get_terminal_size().columns)

    return w


def splitext(path: str) -> tuple[str, str]:
    """Split the pathname `path` into a pair."""
    tail = os.path.split(path)[1]

    sep, extension = tail.rpartition('.')[1:]

    extension = (sep + extension) if sep else sep

    filename = path.removesuffix(extension)

    return filename, extension

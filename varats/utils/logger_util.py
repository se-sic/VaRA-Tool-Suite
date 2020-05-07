"""Utility function for logging."""

import typing as tp


def log_without_linesep(
    log_func: tp.Callable[[str], None]
) -> tp.Callable[[str], None]:
    """Wraps the logger function and strips away all trailing whitespace and
    newline characters, making logs more reable, e.g., for bash and command line
    tool output."""
    return lambda x: log_func(x.rstrip())

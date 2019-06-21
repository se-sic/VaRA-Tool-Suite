"""
Utility module for BenchBuild experiments.
"""

import typing as tp
from plumbum.commands import ProcessExecutionError


class FunctionPEErrorWrapper():
    """
    Wrap a function call with a ProcessExecutionError handler.

    Args:
        handler: function to handle ProcessExecutionError
    """

    def __init__(self, func, handler):
        self.__func = func
        self.__handler = handler

    def __call__(self, *args, **kwargs):
        try:
            return self.__func(*args, **kwargs)
        except ProcessExecutionError as ex:
            self.__handler(ex)


def exec_func_with_pe_error_handler(
        func: tp.Callable[[], tp.Any],
        handler: tp.Callable[[ProcessExecutionError], None]):
    """
    Execute a function call with a ProcessExecutionError handler.

    Args:
        handler: function to handle ProcessExecutionError
    """
    FunctionPEErrorWrapper(func, handler)()

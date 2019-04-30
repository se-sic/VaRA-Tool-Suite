"""
Plot module for util functionality.
"""

import functools


def __check_required_args_impl(required_args, kwargs):
    """
    Implementation to check if all required graph args are passed by the user.
    """
    for arg in required_args:
        if arg not in kwargs:
            raise AssertionError(
                "Argument {} was not specified but is required for this graph."
                .format(arg))


def check_required_args(required_args):
    """
    Check if all required graph args are passed by the user.
    """

    def decorator_pp(func):
        @functools.wraps(func)
        def wrapper_func(*args, **kwargs):
            __check_required_args_impl(required_args, kwargs)
            return func(*args, **kwargs)

        return wrapper_func

    return decorator_pp

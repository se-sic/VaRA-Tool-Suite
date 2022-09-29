#!/usr/bin/env python3
"""This module contains custom exceptions."""

import typing as tp
from functools import wraps


class ProcessTerminatedError(Exception):
    """Raised if a process was terminated."""


class ConfigurationLookupError(Exception):
    """Raised if a paper config could not be found."""


class ConfigurationMapConfigIDMissmatch(Exception):
    """Raised if the config ID parsed from a file did not match the actual
    created ID, this happens when IDs are missing in the file."""


class EmptyOptional(Exception):
    """Raised if an optional was converted to a value without having one."""


T = tp.TypeVar('T')


def unwrap(maybe_t: tp.Optional[T], conversion_reason: str) -> T:
    """
    Unwrap an optional `T` to the underlying type, thowring an exception should
    a conversion not be possible.

    Args:
        maybe_t: the optional that should always be a value
        conversion_reason: why maybe_t should contain a value and unwrapping
                           should be safe

    Returns: the 'contained' value inside the optional
    """
    if not maybe_t:
        raise EmptyOptional(
            "Optional was empty but should contain a value because:"
            f" {conversion_reason}"
        )
    return maybe_t


def auto_unwrap(
    conversion_reason: str
) -> tp.Callable[[tp.Callable[..., tp.Optional[T]]], tp.Callable[..., T]]:
    """
    Wraps a function with an automatic unwrap call, so a function that normally
    returns an optional is declared to always return a concrete value. Should no
    value be returned, an exception is raised mentioning the reason/assumtion
    why it was thought that the function always returns a value.

    Args:
        conversion_reason: why maybe_t should contain a value and unwrapping
                           should be save
    """

    def decorator(
        func_ret_optional: tp.Callable[..., tp.Optional[T]]
    ) -> tp.Callable[..., T]:

        @wraps(func_ret_optional)
        def function_unwrapper(*args: tp.Any, **kwargs: tp.Any) -> T:
            return unwrap(func_ret_optional(*args, **kwargs), conversion_reason)

        return function_unwrapper

    return decorator

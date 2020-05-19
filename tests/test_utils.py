"""Module for test utility functions."""

import typing as tp
from copy import deepcopy

import benchbuild.utils.settings

import varats.settings as settings


def replace_config(
    func: tp.Callable[[tp.Any], tp.Any],
    config: tp.Optional[benchbuild.utils.settings.Configuration] = None
) -> tp.Any:
    """
    Replace the vara config while executing a function.

    This decorator replaces the current vara configuration with a (deep)copy or
    a given config.
    The replaced config is passed as an additional argument to the function.

    Args:
        func: the function to wrap
        config: if given, use this config instead of a copy of the current one

    Returns:
        the wrapped function
    """

    def replace_config_decorator(*args, **kwargs) -> tp.Any:
        old_config = settings.__CFG
        if config:
            new_config = config
        else:
            new_config = deepcopy(old_config)
        settings.__CFG = new_config
        args += (new_config,)
        func(*args, **kwargs)
        settings.__CFG = old_config

    return replace_config_decorator

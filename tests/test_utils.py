"""Module for test utility functions."""
import contextlib
import os
import typing as tp
from copy import deepcopy
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings

import varats.settings as settings

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'


def get_test_config() -> benchbuild.utils.settings.Configuration:
    """
    Get a vara config suitable for testing.

    Configs returned by this function are meant to be passed to
    :func:`replace_config()`.

    Returns:
        a (deep)copy of the current vara config suitable for testing
    """
    test_config = deepcopy(settings._CFG)

    test_config["config_file"] = None
    test_config["data_cache"] = TEST_INPUTS_DIR / "data_cache"
    test_config["result_dir"] = TEST_INPUTS_DIR / "results"

    test_config["paper_config"]["folder"] = TEST_INPUTS_DIR / "paper_config"
    test_config["paper_config"]["current_config"] = None

    # Do not pollute test environment. Tests should use temp dirs.
    test_config["plots"]["plot_dir"] = None
    test_config["tables"]["table_dir"] = None
    test_config["artefacts"]["artefacts_dir"] = None

    return test_config


class _replace_config():

    def __init__(
        self,
        config: tp.Optional[benchbuild.utils.settings.Configuration] = None
    ) -> None:
        self.old_config = get_test_config()
        if config:
            self.new_config = config
        else:
            self.new_config = deepcopy(self.old_config)

    @contextlib.contextmanager
    def decoration_helper(self, args: tp.Any, kwargs: tp.Any) -> tp.Any:
        settings._CFG = self.new_config
        args += (self.new_config,)
        try:
            yield args, kwargs
        finally:
            settings._CFG = self.old_config

    def __call__(self, func) -> tp.Any:

        @wraps(func)
        def wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            with self.decoration_helper(args, kwargs) as (newargs, newkwargs):
                return func(*newargs, **newkwargs)

        return wrapper

    def __enter__(self):
        settings._CFG = self.new_config
        return self.new_config

    def __exit__(self, exc_type, exc_val, exc_tb):
        settings._CFG = self.old_config


def replace_config(
    config: tp.Optional[benchbuild.utils.settings.Configuration] = None
) -> tp.Any:
    """
    Replace the vara config while executing a function.

    This function can be used as a decorator or a context manager.
    It replaces the current vara configuration with a
    :func:`test config<get_test_config()>` or
    a given config.

    If used as a decorator, the replaced config is passed as an additional
    argument to the function.
    If used as a context manager, it binds the replaced config to the name given
    after the `as`.

    Args:
        config: if given, use this config instead of a copy of the current one

    Returns:
        the wrapped function
    """

    return _replace_config(config)

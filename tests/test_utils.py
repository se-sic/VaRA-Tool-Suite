"""Module for test utility functions."""
import contextlib
import os
import tempfile
import typing as tp
from copy import deepcopy
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings

import varats.settings as settings

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'


def get_test_config(tmp_path: Path) -> benchbuild.utils.settings.Configuration:
    """
    Get a vara config suitable for testing.

    Configs returned by this function are meant to be passed to
    :func:`replace_config()`.

    Args:
        tmp_path: path to put files that may be written during test execution

    Returns:
        a (deep)copy of the current vara config suitable for testing
    """
    test_config = deepcopy(settings._CFG)  # pylint: disable=W0212

    # setup test input dir
    test_config["config_file"] = None
    test_config["result_dir"] = TEST_INPUTS_DIR / "results"
    test_config["paper_config"]["folder"] = TEST_INPUTS_DIR / "paper_config"
    test_config["paper_config"]["current_config"] = None

    # let output config options point to test env.
    test_config["data_cache"] = tmp_path / "data_cache"
    test_config["plots"]["plot_dir"] = tmp_path / "plots"
    test_config["tables"]["table_dir"] = tmp_path / "tables"
    test_config["artefacts"]["artefacts_dir"] = tmp_path / "artefacts"

    return test_config


class _ReplaceConfig():

    def __init__(
        self,
        tmp_path: tp.Optional[Path],
        config: tp.Optional[benchbuild.utils.settings.Configuration] = None
    ) -> None:
        if not tmp_path:
            self.tmp_path = tempfile.TemporaryDirectory()
            tmp_path = Path(self.tmp_path.name)

        self.old_config = settings._CFG  # pylint: disable=W0212
        if config:
            self.new_config = config
        else:
            self.new_config = get_test_config(tmp_path)

    @contextlib.contextmanager
    def _decoration_helper(self, args: tp.Any, kwargs: tp.Any) -> tp.Any:
        settings._CFG = self.new_config  # pylint: disable=W0212
        settings.create_missing_folders()
        args += (self.new_config,)
        try:
            yield args, kwargs
        finally:
            settings._CFG = self.old_config  # pylint: disable=W0212
            if self.tmp_path:
                self.tmp_path.cleanup()

    def __call__(self, func) -> tp.Any:

        @wraps(func)
        def wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            with self._decoration_helper(args, kwargs) as (newargs, newkwargs):
                return func(*newargs, **newkwargs)

        return wrapper

    def __enter__(self):
        settings._CFG = self.new_config
        settings.create_missing_folders()
        return self.new_config

    def __exit__(self, exc_type, exc_val, exc_tb):
        settings._CFG = self.old_config
        if self.tmp_path:
            self.tmp_path.cleanup()


def replace_config(
    tmp_path: tp.Optional[Path] = None,
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
        tmp_path: path to put files that may be written during test execution.
                  If absent, the wrapper will create a temporary directory that
                  is deleted after restoring the config.
        config: if given, use this config instead of a copy of the current one

    Returns:
        the wrapped function
    """

    return _ReplaceConfig(tmp_path, config)

"""Module for test utility functions."""
import contextlib
import os
import tempfile
import typing as tp
from copy import deepcopy
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings
import plumbum as pb
from benchbuild.source import Git, base

import varats.utilss.settings as settings

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
    test_config = deepcopy(settings._CFG)  # pylint: disable=protected-access

    # setup test input dir
    test_config["config_file"] = str(tmp_path / ".varats.yml")
    test_config["result_dir"] = str(TEST_INPUTS_DIR / "results")
    test_config["paper_config"]["folder"] = str(
        TEST_INPUTS_DIR / "paper_configs"
    )
    test_config["paper_config"]["current_config"] = None

    # let output config options point to test env.
    test_config["data_cache"] = str(tmp_path / "data_cache")
    test_config["plots"]["plot_dir"] = str(tmp_path / "plots")
    test_config["tables"]["table_dir"] = str(tmp_path / "tables")
    test_config["artefacts"]["artefacts_dir"] = str(tmp_path / "artefacts")

    return test_config


def get_bb_test_config() -> benchbuild.utils.settings.Configuration:
    return deepcopy(settings.bb_cfg())


class _ReplaceConfig():

    def __init__(
        self,
        replace_bb_config: bool = False,
        tmp_path: tp.Optional[Path] = None,
        vara_config: tp.Optional[benchbuild.utils.settings.Configuration
                                ] = None,
        bb_config: tp.Optional[benchbuild.utils.settings.Configuration] = None,
    ) -> None:
        self.replace_bb_config = replace_bb_config
        if self.replace_bb_config:
            # pylint: disable=protected-access
            self.old_bb_config = settings._BB_CFG
            if bb_config:
                self.new_bb_config = bb_config
            else:
                self.new_bb_config = deepcopy(self.old_bb_config)

        if tmp_path:
            self.tmp_path: tp.Optional[tempfile.TemporaryDirectory] = None
        else:
            self.tmp_path = tempfile.TemporaryDirectory()
            tmp_path = Path(self.tmp_path.name)

        # pylint: disable=protected-access
        self.old_config = settings._CFG
        if vara_config:
            self.new_config = vara_config
        else:
            self.new_config = get_test_config(tmp_path)

    @contextlib.contextmanager
    def _decoration_helper(self, args: tp.Any, kwargs: tp.Any) -> tp.Any:
        # pylint: disable=protected-access
        settings._CFG = self.new_config
        settings.create_missing_folders()
        args += (self.new_config,)
        if self.replace_bb_config:
            # pylint: disable=protected-access
            settings._BB_CFG = self.new_bb_config
            args += (self.new_bb_config,)
        try:
            yield args, kwargs
        finally:
            # pylint: disable=protected-access
            settings._CFG = self.old_config
            if self.replace_bb_config:
                # pylint: disable=protected-access
                settings._BB_CFG = self.old_bb_config
            if self.tmp_path:
                self.tmp_path.cleanup()

    def __call__(self, func) -> tp.Any:

        @wraps(func)
        def wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            with self._decoration_helper(args, kwargs) as (newargs, newkwargs):
                return func(*newargs, **newkwargs)

        return wrapper

    def __enter__(self):
        # pylint: disable=protected-access
        settings._CFG = self.new_config
        settings.create_missing_folders()
        if self.replace_bb_config:
            # pylint: disable=protected-access
            settings._BB_CFG = self.new_bb_config
            return self.new_config, self.new_bb_config
        return self.new_config

    def __exit__(self, exc_type, exc_val, exc_tb):
        # pylint: disable=protected-access
        settings._CFG = self.old_config
        if self.replace_bb_config:
            # pylint: disable=protected-access
            settings._BB_CFG = self.old_bb_config
        if self.tmp_path:
            self.tmp_path.cleanup()


def replace_config(
    replace_bb_config: bool = False,
    tmp_path: tp.Optional[Path] = None,
    vara_config: tp.Optional[benchbuild.utils.settings.Configuration] = None,
    bb_config: tp.Optional[benchbuild.utils.settings.Configuration] = None
) -> tp.Any:
    """
    Replace the vara and benchbuild config while executing a (test) function.

    This function can be used as a decorator or a context manager.
    It replaces the current vara or benchbuild configuration with a
    :func:`test config<get_test_config()>` or a given config.

    If used as a decorator, the replaced config is passed as an additional
    argument to the function.
    If used as a context manager, it binds the replaced config to the name given
    after the `as`.

    Args:
        replace_bb_config: whether to also replace the benchbuild config
        tmp_path: path to put files that may be written during test execution.
                  If absent, the wrapper will create a temporary directory that
                  is deleted after restoring the config.
        vara_config: if given, use this as the new vara config instead of a copy
                     of the current one
        bb_config: if given, use this as the new benchbuild config instead of a
                   copy of the current one

    Returns:
        the wrapped function
    """

    return _ReplaceConfig(replace_bb_config, tmp_path, vara_config, bb_config)


class DummyGit(Git):
    """A dummy git source that does nothing."""

    def fetch(self) -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def versions(self) -> tp.List[base.Variant]:
        return []

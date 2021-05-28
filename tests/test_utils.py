"""Module for test utility functions."""
import contextlib
import os
import tempfile
import typing as tp
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings as bb_settings
import plumbum as pb
from benchbuild.source import Git, base

import varats.utils.settings as settings
from varats.tools.bb_config import create_new_bb_config, save_bb_config

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'

TestFunctionTy = tp.Callable[..., tp.Any]


class _TestEnvironment():

    def __init__(self) -> None:

        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.__tmp_path = Path(self.__tmp_dir.name)

        self.__cwd = os.getcwd()

        # pylint: disable=protected-access
        self.__old_config = settings.vara_cfg()
        # pylint: disable=protected-access
        self.__old_bb_config = settings.bb_cfg()

    @contextlib.contextmanager
    def _decoration_helper(self) -> tp.Any:
        self.__enter__()
        try:
            yield
        finally:
            self.__exit__(None, None, None)

    def __call__(self, func: TestFunctionTy) -> TestFunctionTy:

        @wraps(func)
        def wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            with self._decoration_helper():
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self) -> Path:
        os.chdir(self.__tmp_dir.name)
        vara_cfg = settings.create_new_varats_config()
        bb_settings.setup_config(vara_cfg)
        # pylint: disable=protected-access
        settings._CFG = vara_cfg
        settings.save_config()

        bb_cfg = create_new_bb_config(settings.vara_cfg())
        save_bb_config(bb_cfg, settings.vara_cfg())
        # pylint: disable=protected-access
        settings._BB_CFG = bb_cfg

        return self.__tmp_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # pylint: disable=protected-access
        settings._CFG = self.__old_config
        # pylint: disable=protected-access
        settings._BB_CFG = self.__old_bb_config
        os.chdir(self.__cwd)
        if self.__tmp_dir:
            self.__tmp_dir.cleanup()


def run_in_test_environment(test_func: TestFunctionTy) -> TestFunctionTy:
    """
    Run a test in an isolated environment.

    The wrapped test is run inside a temporary directory that acts as the
    varats root folder with a fresh default varats and BenchBuild config.
    The configurations can be accessed via the usual `vara_cfg()` and `bb_cfg()`
    getters.

    Args:
        test_func: the test function to wrap

    Returns:
        the wrapped test function
    """
    return _TestEnvironment()(test_func)


def test_environment() -> _TestEnvironment:
    return _TestEnvironment()


class DummyGit(Git):
    """A dummy git source that does nothing."""

    def fetch(self) -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def versions(self) -> tp.List[base.Variant]:
        return []

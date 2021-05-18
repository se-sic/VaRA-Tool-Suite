"""Module for test utility functions."""
import contextlib
import functools
import os
import tempfile
import typing as tp
from copy import deepcopy
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings
import plumbum as pb
from benchbuild.source import Git, base

import varats.utils.settings as settings

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'


def _get_test_config(tmp_path: Path) -> benchbuild.utils.settings.Configuration:
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

    test_config["config_file"] = str(tmp_path / ".varats.yml")
    test_config["benchbuild_root"] = str(tmp_path / "benchbuild")
    test_config["data_cache"] = str(tmp_path / "data_cache")
    test_config["result_dir"] = str(TEST_INPUTS_DIR / "results")

    test_config["paper_config"]["folder"] = str(
        TEST_INPUTS_DIR / "paper_configs"
    )
    test_config["paper_config"]["current_config"] = None

    # let output config options point to test env.
    test_config["plots"]["plot_dir"] = str(tmp_path / "plots")
    test_config["tables"]["table_dir"] = str(tmp_path / "tables")
    test_config["artefacts"]["artefacts_dir"] = str(tmp_path / "artefacts")

    return test_config


TestFunctionTy = tp.Callable[..., tp.Any]


class _TestEnvironment():

    def __init__(self) -> None:

        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.__tmp_path = Path(self.__tmp_dir.name)

        self.__cwd = os.getcwd()

        # pylint: disable=protected-access
        self.__old_config = settings.vara_cfg()
        self.__new_config = _get_test_config(self.__tmp_path)

        # pylint: disable=protected-access
        self.__old_bb_config = settings.bb_cfg()
        self.__new_bb_config = deepcopy(self.__old_bb_config)

    @contextlib.contextmanager
    def _decoration_helper(self) -> tp.Any:
        # pylint: disable=protected-access
        settings._CFG = self.__new_config
        settings.create_missing_folders()
        # pylint: disable=protected-access
        settings._BB_CFG = self.__new_bb_config
        try:
            yield
        finally:
            # pylint: disable=protected-access
            settings._CFG = self.__old_config
            # pylint: disable=protected-access
            settings._BB_CFG = self.__old_bb_config
            if self.__tmp_dir:
                self.__tmp_dir.cleanup()

    def __call__(self, func: TestFunctionTy) -> TestFunctionTy:

        @wraps(func)
        def wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            with self._decoration_helper():
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self) -> Path:
        os.chdir(self.__tmp_dir.name)
        # pylint: disable=protected-access
        settings._CFG = self.__new_config
        settings.create_missing_folders()
        # pylint: disable=protected-access
        settings._BB_CFG = self.__new_bb_config
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

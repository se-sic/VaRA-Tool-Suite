"""Module for test utility functions."""
import contextlib
import os
import shutil
import tempfile
import typing as tp
from functools import wraps
from pathlib import Path

import benchbuild.utils.settings as bb_settings
import plumbum as pb
from benchbuild.source import Git, base

import varats.utils.settings as settings
from varats.base.configuration import ConfigurationImpl, ConfigurationOptionImpl
from varats.tools.bb_config import create_new_bb_config

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'

TestFunctionTy = tp.Callable[..., tp.Any]


class UnitTestInputs():

    class UnitTestInput():

        def __init__(self, src: Path, dst: Path):
            self.__src = src
            self.__dst = dst

        def copy_to_path(self, path):
            dst = path / self.__dst
            if self.__src.is_dir():
                shutil.copytree(self.__src, dst)
            else:
                shutil.copy(self.__src, dst)

    PAPER_CONFIGS = UnitTestInput(
        TEST_INPUTS_DIR / "paper_configs", Path("paper_configs")
    )
    RESULT_FILES = UnitTestInput(TEST_INPUTS_DIR / "results", Path("results"))
    PLOTS = UnitTestInput(TEST_INPUTS_DIR / "plots", Path("plots"))
    TABLES = UnitTestInput(TEST_INPUTS_DIR / "tables", Path("tables"))
    ARTEFACTS = UnitTestInput(TEST_INPUTS_DIR / "artefacts", Path("artefacts"))

    @staticmethod
    def create_test_input(src: Path, dst: Path) -> UnitTestInput:
        return UnitTestInputs.UnitTestInput(src, dst)


class _TestEnvironment():

    def __init__(
        self, required_test_inputs: tp.Iterable[UnitTestInputs.UnitTestInput]
    ) -> None:

        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.__tmp_path = Path(self.__tmp_dir.name)
        self.__cwd = os.getcwd()

        if required_test_inputs:
            for test_input in required_test_inputs:
                test_input.copy_to_path(self.__tmp_path)

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
        settings.save_bb_config(bb_cfg)
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


def run_in_test_environment(
    *required_test_inputs: UnitTestInputs.UnitTestInput
) -> TestFunctionTy:
    """
    Run a test in an isolated test environment.

    The wrapped test is run inside a temporary directory that acts as the
    varats root folder with a fresh default varats and BenchBuild config.
    The configurations can be accessed via the usual `vara_cfg()` and `bb_cfg()`
    getters.

    Args:
        required_test_inputs: test inputs to be copied into the test environment

    Returns:
        the wrapped test function
    """

    def wrapper_func(test_func: TestFunctionTy) -> TestFunctionTy:
        return _TestEnvironment(required_test_inputs)(test_func)

    return wrapper_func


def test_environment(
    *required_test_inputs: UnitTestInputs.UnitTestInput
) -> _TestEnvironment:
    """
    Context manager that creates an isolated test environment.

    The wrapped test is run inside a temporary directory that acts as the
    varats root folder with a fresh default varats and BenchBuild config.
    The configurations can be accessed via the usual `vara_cfg()` and `bb_cfg()`
    getters.

    Args:
        required_test_inputs: test inputs to be copied into the test environment
    """
    return _TestEnvironment(required_test_inputs)


class DummyGit(Git):
    """A dummy git source that does nothing."""

    def fetch(self) -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        return pb.LocalPath("/dev/null")

    def versions(self) -> tp.List[base.Variant]:
        return []


class ConfigurationHelper:
    """This class is a helper for various tests."""

    @staticmethod
    def create_test_config() -> 'ConfigurationImpl':
        """This method creates a test configuration."""
        test_config = ConfigurationImpl()
        test_config.add_config_option(ConfigurationOptionImpl("foo", True))
        test_config.add_config_option(ConfigurationOptionImpl("bar", False))
        test_config.add_config_option(
            ConfigurationOptionImpl("bazz", "bazz-value")
        )
        test_config.add_config_option(ConfigurationOptionImpl("buzz", "None"))
        return test_config

"""Module for test utility functions."""
import contextlib
import os
import shutil
import sys
import tempfile
import typing as tp
from functools import wraps
from pathlib import Path
from threading import Lock

import benchbuild.source.base as base
import benchbuild.utils.settings as bb_settings
import plumbum as pb
from benchbuild import Project
from benchbuild.source import Git
from benchbuild.utils.cmd import git

import varats.utils.settings as settings
from varats.base.configuration import ConfigurationImpl, ConfigurationOptionImpl
from varats.project.project_util import is_git_source
from varats.tools.bb_config import create_new_bb_config

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol
else:
    from typing import Protocol

TEST_INPUTS_DIR = Path(os.path.dirname(__file__)) / 'TEST_INPUTS'

TestFunctionTy = tp.Callable[..., tp.Any]


class UnitTestFixture(Protocol):
    """A test fixture that can be used with a :class:`TestEnvironment`."""

    def copy_to_env(self, path: Path) -> None:
        """
        Called when entering the test environment.

        The new configs are already in place and the cwd is the tmp dir.
        """
        ...

    def cleanup(self) -> None:
        """
        Called when exiting the test environment.

        The old configs are in place again, but the cwd is still the tmp dir.
        """
        ...


class FileFixture(UnitTestFixture):
    """A file or directory that is copied into the test environment."""

    def __init__(self, src: Path, dst: Path):
        self.__src = src
        self.__dst = dst

    def copy_to_env(self, path: Path) -> None:
        dst = path / self.__dst
        if self.__src.is_dir():
            if self.__dst.exists():
                self.__dst.rmdir()
            shutil.copytree(self.__src, dst)
        else:
            shutil.copy(self.__src, dst)

    def cleanup(self) -> None:
        pass


class RepoFixture(UnitTestFixture):
    """
    A git repository that is cloned into the test environment.

    The clone uses a local reference to avoid unnecessary traffic.
    """

    def __init__(self, source: Git):
        self.__repo_name = source.local
        self.__local = source.fetch()
        self.__remote = source.remote
        self.__lock = Lock()

    def copy_to_env(self, path: Path) -> None:
        with self.__lock:
            bb_tmp = str(path / "benchbuild/tmp")
            settings.bb_cfg()["tmp_dir"] = bb_tmp
            base.CFG["tmp_dir"] = bb_tmp
            git(
                "clone", "--dissociate", "--recurse-submodules", "--reference",
                self.__local, self.__remote, f"{bb_tmp}/{self.__repo_name}"
            )

    def cleanup(self) -> None:
        bb_tmp = str(settings.bb_cfg()["tmp_dir"])
        base.CFG["tmp_dir"] = bb_tmp


class UnitTestFixtures():
    """Collection/factory for test fixtures."""
    PAPER_CONFIGS = FileFixture(
        TEST_INPUTS_DIR / "paper_configs", Path("paper_configs")
    )
    RESULT_FILES = FileFixture(TEST_INPUTS_DIR / "results", Path("results"))
    PLOTS = FileFixture(TEST_INPUTS_DIR / "plots", Path("plots"))
    TABLES = FileFixture(TEST_INPUTS_DIR / "tables", Path("tables"))
    ARTEFACTS = FileFixture(TEST_INPUTS_DIR / "artefacts", Path("artefacts"))

    # Projects available for testing:
    # BROTLI = RepoFixture.for_project(Brotli)
    TEST_PROJECTS = RepoFixture(
        Git(
            remote="https://github.com/se-sic/vara-test-repos",
            local="vara_test_repos",
            refspec="origin/HEAD",
            shallow=False,
            limit=None
        )
    )

    @staticmethod
    def create_file_fixture(src: Path, dst: Path) -> UnitTestFixture:
        """Creates a file fixture."""
        return FileFixture(src, dst)

    @staticmethod
    def create_project_repo_fixture(project: tp.Type[Project]) -> RepoFixture:
        """Creates a repo fixture for the main source of a project."""
        source = project.SOURCE[0]
        if not is_git_source(source):
            raise AssertionError(
                f"Primary source of project {project.NAME}"
                "is not a git repository."
            )
        return RepoFixture(source)


class TestEnvironment():
    """
    Test environment implementation.

    The wrapped test is run inside a temporary directory that acts as the
    varats root folder with a fresh default varats and BenchBuild config.
    The configurations can be accessed via the usual `vara_cfg()` and `bb_cfg()`
    getters.

    Args:
        required_test_inputs: test inputs to be copied into the test environment
    """

    def __init__(
        self, required_test_inputs: tp.Iterable[UnitTestFixture]
    ) -> None:

        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.__tmp_path = Path(self.__tmp_dir.name)
        self.__cwd = os.getcwd()
        self.__test_inputs = required_test_inputs

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
        # make new bb_cfg point to old tmp to avoid multiple git clones
        bb_cfg["tmp_dir"] = str(self.__old_bb_config["tmp_dir"])

        settings.save_bb_config(bb_cfg)
        # pylint: disable=protected-access
        settings._BB_CFG = bb_cfg

        for test_input in self.__test_inputs:
            test_input.copy_to_env(self.__tmp_path)

        return self.__tmp_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # pylint: disable=protected-access
        settings._CFG = self.__old_config
        # pylint: disable=protected-access
        settings._BB_CFG = self.__old_bb_config

        for test_input in self.__test_inputs:
            test_input.cleanup()

        os.chdir(self.__cwd)
        if self.__tmp_dir:
            self.__tmp_dir.cleanup()


def run_in_test_environment(
    *required_test_inputs: UnitTestFixture
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
        return TestEnvironment(required_test_inputs)(test_func)

    return wrapper_func


def test_environment(*required_test_inputs: UnitTestFixture) -> TestEnvironment:
    """
    Context manager that creates an isolated test environment.

    The wrapped test is run inside a temporary directory that acts as the
    varats root folder with a fresh default varats and BenchBuild config.
    The configurations can be accessed via the usual `vara_cfg()` and `bb_cfg()`
    getters.

    Args:
        required_test_inputs: test inputs to be copied into the test environment
    """
    return TestEnvironment(required_test_inputs)


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

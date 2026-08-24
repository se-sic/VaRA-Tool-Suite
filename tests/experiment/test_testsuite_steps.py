import typing as tp
import unittest
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from benchbuild.utils.actions import StepResult
from helper_utils import run_in_test_environment
from plumbum import ProcessExecutionError

from tests.utils.test_experiment_util import BBTestProject
from varats.experiment.steps.testsuite import (
    BuildTestSuite,
    CollectTests,
    PrepareTestSuite,
    RunTestSuite,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.testsuite_utils import TestResult

if tp.TYPE_CHECKING:
    # pylint: disable=W0611
    from varats.project.project_util import ProjectBinaryWrapper


def _identity_decorator(func):
    return func


with (
    mock.patch(
        "benchbuild.utils.run.in_builddir", return_value=_identity_decorator
    ),
    mock.patch("benchbuild.utils.run.store_config", side_effect=lambda f: f),
):

    class TestsuiteProject(BBTestProject, VProject):
        """A test project that implements the TestSuite protocol."""

        def __init__(
            self, test_results: dict[str, TestResult], error: bool = False
        ):
            super().__init__()
            self.prepare_called = False
            self.build_called = False
            self.run_called = False
            self.get_names_called = False
            self.__test_results = test_results
            self.__error = error

        @staticmethod
        def binaries_for_revision(
            revision: ShortCommitHash,
        ) -> list['ProjectBinaryWrapper']:
            pass

        def prepare_test_environment(self) -> None:
            """Prepare the test environment."""
            self.prepare_called = True
            if self.__error:
                raise ProcessExecutionError(
                    "Test error", 1, "Test error", "Test error"
                )

        def build_tests(self) -> None:
            """Build the tests."""
            self.build_called = True
            if self.__error:
                raise ProcessExecutionError(
                    "Test error", 1, "Test error", "Test error"
                )

        def run_testsuite(
            self,
            test_report_path: Path | None = None,  # noqa: ARG002
            tests_to_run: Iterable[str] | None = None,  # noqa: ARG002
            tests_to_exclude: Iterable[str] | None = None,  # noqa: ARG002
        ) -> dict[str, TestResult]:
            """Run the test suite."""
            self.run_called = True
            if self.__error:
                raise ProcessExecutionError(
                    "Test error", 1, "Test error", "Test error"
                )
            return self.__test_results

        def get_test_names(self) -> Iterable[str]:
            """Get the names of the tests."""
            self.get_names_called = True
            if self.__error:
                raise ProcessExecutionError(
                    "Test error", 1, "Test error", "Test error"
                )
            return self.__test_results.keys()


class TestTestsuiteSteps(unittest.TestCase):
    """Tests for the TestSuite steps."""

    @run_in_test_environment()
    def setUp(self) -> None:
        """Set up the test project."""
        self.project = TestsuiteProject(
            {
                "test1": TestResult.PASSED,
                "test2": TestResult.PASSED,
                "test3": TestResult.PASSED,
            }
        )

    @run_in_test_environment()
    def test_prepare_test_environment(self) -> None:
        """Test that prepare_test_environment() can be called."""
        self.assertFalse(self.project.prepare_called)
        prepare_step = PrepareTestSuite(self.project)
        prepare_step()

        self.assertTrue(self.project.prepare_called)
        self.assertEqual(prepare_step.status, StepResult.OK)

    @run_in_test_environment()
    def test_build_tests(self) -> None:
        """Test that build_tests() can be called."""
        project = TestsuiteProject(
            {
                "test1": TestResult.PASSED,
                "test2": TestResult.PASSED,
                "test3": TestResult.PASSED,
            }
        )
        self.assertFalse(project.build_called)
        build_step = BuildTestSuite(project)
        build_step()

        self.assertTrue(project.build_called)
        self.assertEqual(build_step.status, StepResult.OK)

    @run_in_test_environment()
    def test_run_testsuite(self) -> None:
        """Test that run_testsuite() returns the expected results."""
        self.assertFalse(self.project.run_called)
        with TemporaryDirectory() as tmp_dir:
            run_step = RunTestSuite(
                self.project, Path(tmp_dir) / "results.json"
            )
            run_step()

        self.assertTrue(self.project.run_called)
        self.assertEqual(run_step.status, StepResult.OK)

        with TemporaryDirectory() as tmp_dir:
            # New run step with a failing test result
            run_step = RunTestSuite(
                TestsuiteProject(
                    {
                        "test1": TestResult.PASSED,
                        "test2": TestResult.FAILED,
                        "test3": TestResult.PASSED,
                    }
                ),
                Path(tmp_dir) / "results.json",
            )
            run_step()

            self.assertEqual(run_step.status, StepResult.ERROR)

    @run_in_test_environment()
    def test_get_test_names(self) -> None:
        """Test that get_test_names() returns the expected test names."""
        with TemporaryDirectory() as tmp_dir:
            collect_step = CollectTests(
                self.project, Path(tmp_dir) / "results.json"
            )
            collect_step()

        self.assertEqual(collect_step.status, StepResult.OK)


class TestInvalidProjectTypes(unittest.TestCase):
    """Tests for invalid project types."""

    def test_prepare_test_environment_invalid_project(self) -> None:
        """
        Test prepare_test_environment().

        Check whether it raises for invalid project types.
        """
        with self.assertRaises(TypeError):
            PrepareTestSuite(BBTestProject())()

    def test_build_tests_invalid_project(self) -> None:
        """Test that build_tests() raises for invalid project types."""
        with self.assertRaises(TypeError):
            BuildTestSuite(BBTestProject())()

    def test_run_testsuite_invalid_project(self) -> None:
        """Test that run_testsuite() raises for invalid project types."""
        with self.assertRaises(TypeError):
            RunTestSuite(BBTestProject(), Path("/tmp/results.json"))()

    def test_get_test_names_invalid_project(self) -> None:
        """Test that get_test_names() raises for invalid project types."""
        with self.assertRaises(TypeError):
            CollectTests(BBTestProject(), Path("/tmp/results.json"))()


class TestErrorSteps(unittest.TestCase):
    """Tests for error steps."""

    @run_in_test_environment()
    def test_run_testsuite_error(self) -> None:
        """Tests run_testsuite() with ProcessExecutionError."""
        project = TestsuiteProject({}, error=True)
        step = RunTestSuite(project, Path("/tmp/results.json"))
        step()

        self.assertTrue(project.run_called)
        self.assertEqual(step.status, StepResult.ERROR)

    @run_in_test_environment()
    def test_prepare_test_environment_error(self) -> None:
        """Tests prepare_test_environment() with ProcessExecutionError."""
        project = TestsuiteProject({}, error=True)
        step = PrepareTestSuite(project)
        step()

        self.assertTrue(project.prepare_called)
        self.assertEqual(step.status, StepResult.ERROR)

    @run_in_test_environment()
    def test_build_tests_error(self) -> None:
        """Tests build_tests() when ProcessExecutionError occurs."""
        project = TestsuiteProject({}, error=True)
        step = BuildTestSuite(project)
        step()

        self.assertTrue(project.build_called)
        self.assertEqual(step.status, StepResult.ERROR)

    @run_in_test_environment()
    def test_get_test_names_error(self) -> None:
        """Tests get_test_names() when ProcessExecutionError occurs."""
        project = TestsuiteProject({}, error=True)
        step = CollectTests(project, Path("/tmp/results.json"))
        step()

        self.assertTrue(project.get_names_called)
        self.assertEqual(step.status, StepResult.ERROR)

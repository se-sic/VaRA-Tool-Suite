import typing as tp
import unittest
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from benchbuild.utils.actions import StepResult

from tests.utils.test_experiment_util import BBTestProject
from varats.experiment.steps.testsuite import (
    BuildTestSuite,
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

        def __init__(self, test_results: dict[str, TestResult]):
            super().__init__()
            self.prepare_called = False
            self.build_called = False
            self.run_called = False
            self.get_names_called = False
            self.__test_results = test_results

        @staticmethod
        def binaries_for_revision(
            revision: ShortCommitHash,
        ) -> list['ProjectBinaryWrapper']:
            pass

        def prepare_test_environment(self) -> None:
            """Prepare the test environment."""
            self.prepare_called = True

        def build_tests(self) -> None:
            """Build the tests."""
            self.build_called = True

        def run_testsuite(
            self,
            test_report_path: Path | None = None,  # noqa: ARG002
            tests_to_run: Iterable[str] | None = None,  # noqa: ARG002
            tests_to_exclude: Iterable[str] | None = None,  # noqa: ARG002
        ) -> dict[str, TestResult]:
            """Run the test suite."""
            self.run_called = True
            return self.__test_results

        def get_test_names(self) -> Iterable[str]:
            """Get the names of the tests."""
            self.get_names_called = True
            return self.__test_results.keys()


class TestTestsuiteSteps(unittest.TestCase):
    """Tests for the TestSuite steps."""

    def setUp(self) -> None:
        """Set up the test project."""
        self.project = TestsuiteProject(
            {
                "test1": TestResult.PASSED,
                "test2": TestResult.PASSED,
                "test3": TestResult.PASSED,
            }
        )

    def test_prepare_test_environment(self) -> None:
        """Test that prepare_test_environment() can be called."""
        self.assertFalse(self.project.prepare_called)
        prepare_step = PrepareTestSuite(self.project)
        prepare_step()

        self.assertTrue(self.project.prepare_called)
        self.assertEqual(prepare_step.status, StepResult.OK)

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

    def test_get_test_names(self) -> None:
        """Test that get_test_names() returns the expected test names."""
        test_names = list(self.project.get_test_names())
        self.assertListEqual(test_names, ["test1", "test2", "test3"])

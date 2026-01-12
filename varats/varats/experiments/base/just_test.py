"""Experiments for simple test execution."""
import typing as tp
from pathlib import Path

from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions

from varats.data.reports.testsuite_report import TestsuiteReport
from varats.data.reports.text_report import PlainTextReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
)
from varats.experiment.steps.testsuite import (
    RunTestSuite,
    PrepareTestSuite,
    BuildTestSuite,
    CollectTests,
)
from varats.experiment.wllvm import RunWLLVM
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class JustTest(VersionExperiment, shorthand="JT"):
    """Generates empty report file."""

    NAME = "JustTest"

    REPORT_SPEC = ReportSpecification(TestsuiteReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        fake_binary = ProjectBinaryWrapper(
            "TESTSUITE", Path(), BinaryType.EXECUTABLE
        )

        result_file = create_new_success_result_filepath(
            self.get_handle(), TestsuiteReport, project, fake_binary,
            get_current_config_id(project)
        )

        analysis_actions = [
            PrepareTestSuite(project),
            BuildTestSuite(project),
            RunTestSuite(project, Path(result_file.full_path())),
            actions.Clean(project)
        ]

        return analysis_actions


class CollectTestNames(VersionExperiment, shorthand="CTN"):
    """Collects test names from the test suite."""

    NAME = "CollectTestNames"
    REPORT_SPEC = ReportSpecification(PlainTextReport)

    project: VProject

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << RunWLLVM() \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        fake_binary = ProjectBinaryWrapper(
            "TESTSUITE", Path(), BinaryType.EXECUTABLE
        )

        result_file = create_new_success_result_filepath(
            self.get_handle(), PlainTextReport, project, fake_binary,
            get_current_config_id(project)
        )

        analysis_actions = [
            PrepareTestSuite(project),
            CollectTests(project,
                         result_file.full_path().absolute()),
            actions.Clean(project)
        ]

        return analysis_actions

"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import os
import typing as tp

from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import time_cmd
from plumbum import local

from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    ExperimentHandle,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
)
from varats.project.project_util import BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.report import FileStatusExtension as FSE
from varats.report.tef_report import TEFReport
from varats.report.gnu_time_report import TimeReport

# TODO: Refactor to use a bass class for experiments to avoid code duplication
# where possible


class TimeBinary(actions.Step):
    """Executes the specified binaries and record the time it took to run"""

    NAME = "TimeBinary"
    DESCRIPTION = "Executes each binary and times it"

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.time_run)  # type: ignore
        self.__experiment_handle = experiment_handle

    def time_run(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        project: Project = self.obj

        print(f"PWD {os.getcwd()}")

        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:  # type: ignore[attr-defined]
            if binary.type != BinaryType.EXECUTABLE:
                continue

            result_file = self.__experiment_handle.get_file_name(
                TimeReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,  # type: ignore
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS,
            )

            with local.cwd(local.path(project.source_of_primary)):
                print(f"Currently at {local.path(project.source_of_primary)}")
                print(f"Bin path {binary.path}")
                time_cmd = local["/usr/bin/time"]
                run_cmd = time_cmd[
                    "-o", f"{vara_result_folder}/{result_file}", "-v", binary.path
                ]
                # REVIEW: Is this correct ? Copied it from JustCompile
                exec_func_with_pe_error_handler(
                    run_cmd,
                    create_default_analysis_failure_handler(
                        self.__experiment_handle,
                        project,
                        TimeReport,
                        Path(vara_result_folder),
                    ),
                )

        return actions.StepResult.OK


class ExecAndTraceBinary(actions.Step):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads."""

    NAME = "ExecBinary"
    DESCRIPTION = "Executes each binary and white-box performance traces."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.run_perf_tracing)  # type: ignore
        self.__experiment_handle = experiment_handle

    def run_perf_tracing(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        project: Project = self.obj

        print(f"PWD {os.getcwd()}")

        vara_result_folder = get_varats_result_folder(project)
        for binary in project.binaries:  # type: ignore[attr-defined]
            if binary.type != BinaryType.EXECUTABLE:
                continue

            result_file = self.__experiment_handle.get_file_name(
                TEFReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS,
            )

            with local.cwd(local.path(project.source_of_primary)):
                print(f"Currently at {local.path(project.source_of_primary)}")
                print(f"Bin path {binary.path}")
                executable = local[f"{binary.path}"]
                with local.env(VARA_TRACE_FILE=f"{vara_result_folder}/{result_file}"):
                    executable()

        return actions.StepResult.OK


class RunTracedTEF(VersionExperiment, shorthand="RTTEF"):
    """Build and run the traced version of the binary"""

    NAME = "RunTraced"

    REPORT_SPEC = ReportSpecification(TEFReport)

    def actions_for_project(self, project: Project) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # Sets FM model flags
        project.cflags += ["-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"]
        # Sets vara tracing flags
        project.cflags += ["-fsanitize=vara", "-fvara-instr=trace_event"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = (
            run.RuntimeExtension(project, self) << time.RunWithTime()
        )

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = (
            compiler.RunCompiler(project, self) << run.WithTimeout()
        )

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(ExecAndTraceBinary(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunTracedTime(VersionExperiment, shorthand="RTTIME"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedTime"

    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(self, project: Project) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # Sets FM model flags
        project.cflags += ["-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"]
        # Sets vara tracing flags
        project.cflags += ["-fsanitize=vara", "-fvara-instr=trace_event"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = (
            run.RuntimeExtension(project, self) << time.RunWithTime()
        )

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = (
            compiler.RunCompiler(project, self) << run.WithTimeout()
        )

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TimeReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(TimeBinary(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunUntraced(VersionExperiment, shorthand="RU"):
    """Build and run the untraced version of the binary"""

    NAME = "RunUntraced"

    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(self, project: Project) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = (
            run.RuntimeExtension(project, self) << time.RunWithTime()
        )

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = (
            compiler.RunCompiler(project, self) << run.WithTimeout()
        )

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TimeReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(TimeBinary(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""Module for feature performance eperiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import typing as tp

from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    create_new_success_result_filepath, get_default_compile_error_wrapped,
    get_default_compile_error_wrapped, ZippedExperimentSteps
)
from varats.report.report import ReportSpecification
from varats.report.gnu_time_report import TimeReport
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.base.time_workloads import TimeProjectWorkloads

from varats.project.varats_project import VProject


class RunTracedUnoptimized(FeatureExperiment, shorthand="RTUnopt"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedUnoptimized"
    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = "trace_event"  # trace_event

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type)

        project.ldflags += self.get_vara_tracing_ldflags()

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

        measurement_reps = 5

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))

        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimeProjectWorkloads(project, num, binary)
                        for num in range(measurement_reps)
                    ]
                )
            )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunTracedNaive(FeatureExperiment, shorthand="RTNaive"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedNaiveOptimization"
    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = "trace_event"  # trace_event

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type)

        project.cflags += ["-mllvm", "--vara-optimizer-policy=naive"]

        project.ldflags += self.get_vara_tracing_ldflags()

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

        measurement_reps = 5

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimeProjectWorkloads(project, num, binary)
                        for num in range(measurement_reps)
                    ]
                )
            )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunUntraced(FeatureExperiment, shorthand="RU"):
    """Build and run the untraced version of the binary"""

    NAME = "RunUntraced"

    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
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

        measurement_reps = 5

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))

        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimeProjectWorkloads(project, num, binary)
                        for num in range(measurement_reps)
                    ]
                )
            )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

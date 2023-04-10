from abc import abstractmethod
import typing as tp
import textwrap

from plumbum import local

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    create_new_success_result_filepath, get_default_compile_error_wrapped,
    ExperimentHandle, exec_func_with_pe_error_handler,
    create_default_analysis_failure_handler
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
)
from varats.report.report import ReportSpecification
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import FeatureExperiment, ProjectStep
from varats.data.reports.dynamic_overhead_report import DynamicOverheadReport
from varats.provider.workload.workload_provider import WorkloadProvider

from varats.project.project_util import ProjectBinaryWrapper

from varats.project.varats_project import VProject

from varats.ts_utils.cli_util import tee


class Runner(FeatureExperiment, shorthand="R"):

    @abstractmethod
    def set_vara_flags(self, project: VProject) -> VProject:
        return project

    @abstractmethod
    def get_analysis_actions(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        return []

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        self.set_vara_flags(project)

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
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))

        analysis_actions.extend(self.get_analysis_actions(project))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class DynamicOverheadAnalysis(ProjectStep):

    def __init__(
        self, project: Project, experiment: ExperimentHandle,
        binary: ProjectBinaryWrapper
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__experiment_handle = experiment

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* Compute dynamic overhead for binary {self.__binary.path}",
            indent * " "
        )

    def analyze(self) -> actions.StepResult:
        """Only create a report file."""
        with local.cwd(self.project.builddir):
            for prj_command in workload_commands(
                self.project, self.__binary,
                [WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL]
            ):
                result_file = create_new_success_result_filepath(
                    self.__experiment_handle, DynamicOverheadReport,
                    self.project, self.__binary
                )
                pb_cmd = prj_command.command.as_plumbum(project=self.project)
                print("##################", pb_cmd)

                run_cmd = pb_cmd > str(result_file)

                run_cmd()

                # exec_func_with_pe_error_handler(
                #     run_cmd,
                #     create_default_analysis_failure_handler(
                #         self.__experiment_handle, self.project,
                #         DynamicOverheadReport
                #     )
                # )

        return actions.StepResult.OK


class DynamicOverheadRunner(Runner, shorthand="CDO"):
    NAME = "ComputeDynamicOverhead"
    REPORT_SPEC = ReportSpecification(DynamicOverheadReport)

    @property
    @abstractmethod
    def optimizer_policy(self) -> str:
        return "none"

    def get_analysis_actions(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:

        return [
            DynamicOverheadAnalysis(project, self.get_handle(), binary)
            for binary in project.binaries
            if binary.type == BinaryType.EXECUTABLE
        ]

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* Compute dynamic overhead with policy {self.optimizer_policy} for binary {self.__binary.path}",
            indent * " "
        )

    def set_vara_flags(self, project: VProject) -> VProject:
        instr_type = "print"

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type)

        project.cflags += [
            "-mllvm", f"-vara-optimizer-policy={self.optimizer_policy}"
        ]

        project.ldflags += self.get_vara_tracing_ldflags()

        return project


class DynamicOverheadOptimizedNaive(
    DynamicOverheadRunner, shorthand=DynamicOverheadRunner.SHORTHAND + "N"
):
    NAME = "ComputeDynamicOverheadNaive"

    @property
    def optimizer_policy(self) -> str:
        return "naive"


class DynamicOverheadOptimizedAlternating(
    DynamicOverheadRunner, shorthand=DynamicOverheadRunner.SHORTHAND + "A"
):
    NAME = "ComputeDynamicOverheadAlternating"

    @property
    def optimizer_policy(self) -> str:
        return "alternating"

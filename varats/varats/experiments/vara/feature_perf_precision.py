"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import textwrap
import typing as tp
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.actions import (
    ProjectStep,
    Step,
    StepResult,
    Compile,
    Clean,
)
from plumbum import local

from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    WithUnlimitedStackSize,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_current_config_id,
    get_default_compile_error_wrapped,
    get_extra_config_options,
)
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    RunVaRATracedXRayWorkloads,
    FeatureInstrType,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReport


class RunTEFTracedWorkloads(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
        report_file_ending: str = "json"
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__report_file_ending = report_file_ending

    def __call__(self) -> StepResult:
        return self.run_traced_code()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                # Skip libaries as we cannot run them
                continue

            result_filepath = create_new_success_result_filepath(
                self.__experiment_handle,
                self.__experiment_handle.report_spec().main_report,
                self.project, binary, get_current_config_id(self.project)
            )

            with local.cwd(local.path(self.project.builddir)):
                with ZippedReportFolder(result_filepath.full_path()) as tmp_dir:
                    for prj_command in workload_commands(
                        self.project, binary, [WorkloadCategory.EXAMPLE]
                    ):
                        local_tracefile_path = Path(
                            tmp_dir
                        ) / f"trace_{prj_command.command.label}" \
                            f".{self.__report_file_ending}"
                        with local.env(VARA_TRACE_FILE=local_tracefile_path):
                            pb_cmd = prj_command.command.as_plumbum(
                                project=self.project
                            )
                            print(
                                f"Running example {prj_command.command.label}"
                            )

                            extra_options = get_extra_config_options(
                                self.project
                            )
                            with cleanup(prj_command):
                                pb_cmd(
                                    *extra_options,
                                    retcode=binary.valid_exit_codes
                                )

        return StepResult.OK


class TEFProfileRunner(FeatureExperiment, shorthand="TEFp"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfiler"

    REPORT_SPEC = ReportSpecification(TEFReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = FeatureInstrType.TEF

        project.cflags += self.get_vara_feature_cflags(project)

        threshold = 0 if project.DOMAIN.value is ProjectDomains.TEST else 100
        project.cflags += self.get_vara_tracing_cflags(
            instr_type, project=project, instruction_threshold=threshold
        )

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

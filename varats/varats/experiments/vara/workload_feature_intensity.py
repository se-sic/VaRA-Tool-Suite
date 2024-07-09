import textwrap
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb_ext
from benchbuild import Project
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import Step, StepResult
from plumbum import local

from varats.data.reports.runtime_feature_instrumentation import (
    RunTimeFeatureInstrAggReport,
)
from varats.experiment.experiment_util import (
    WithUnlimitedStackSize,
    get_default_compile_error_wrapped,
    get_config_patch_steps,
    create_new_success_result_filepath,
    OutputFolderStep,
    ZippedExperimentSteps,
)
from varats.experiment.workload_util import (
    workload_commands,
    create_workload_specific_filename,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.experiments.vara.feature_perf_precision import (
    select_project_binaries,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class WorkloadFeatureRegions(OutputFolderStep):

    def __init__(self, project: Project, binary: ProjectBinaryWrapper):
        super().__init__(project=project)
        self.__binary = binary
        self.__workload_commands = workload_commands(
            self.project, self.__binary
        )

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* WorkloadFeatureRegions for {len(self.__workload_commands)} workloads",
            indent * " "
        )

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> StepResult:
        with local.cwd(self.project.builddir):
            for prj_command in self.__workload_commands:
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "feature_intensity",
                    prj_command.command,
                    file_suffix=".txt"
                )

                print(f"Running workload command: {pb_cmd}")

                with cleanup(prj_command):
                    # noinspection PyStatementEffect
                    with local.env(VARA_TRACE_FILE=run_report_name):
                        (pb_cmd)()

        return actions.StepResult.OK


class WorkloadFeatureIntensity(FeatureExperiment, shorthand="WFI"):

    NAME = "WorkloadFeatureIntensity"
    DESCRIPTION = "Collects feature intensity data for all project example workloads."

    REPORT_SPEC = ReportSpecification(RunTimeFeatureInstrAggReport)

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += ["-disable-llvm-optzns", "-O0", "-g"]

        project.cflags += self.get_vara_tracing_cflags(
            FeatureInstrType.TEF,
            project=project,
            save_temps=False,
            instruction_threshold=0
        )

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = get_config_patch_steps(project)
        analysis_actions.append(actions.Compile(project))

        for binary in select_project_binaries(project):
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary,
                get_current_config_id(project)
            )

            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath,
                    [WorkloadFeatureRegions(project=project, binary=binary)]
                )
            )

            analysis_actions.append(actions.Clean(project))

            return analysis_actions

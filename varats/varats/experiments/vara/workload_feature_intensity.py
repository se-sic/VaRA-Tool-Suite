import textwrap
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb_ext
from benchbuild import Project
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import Step, StepResult
from plumbum import local

from varats.data.reports.FeatureIntensity import WorkloadFeatureIntensityReport
from varats.experiment.experiment_util import (
    WithUnlimitedStackSize,
    get_default_compile_error_wrapped,
    get_config_patch_steps,
    OutputFolderStep,
    ZippedExperimentSteps,
    get_varats_result_folder,
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
from varats.report.report import (
    ReportSpecification,
    ReportFilename,
    FileStatusExtension,
    ReportFilepath,
)
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash


class WorkloadFeatureRegions(OutputFolderStep):

    def __init__(self, project: Project, binary: ProjectBinaryWrapper):
        super().__init__(project=project)
        self.__binary = binary
        self.__workload_commands = workload_commands(
            self.project, self.__binary
        )

    def __str__(self, indent: int = 0) -> str:
        repr = textwrap.indent(
            f"* WorkloadFeatureRegions: Run workloads for binary '{self.__binary.name}'\n",
            indent * " "
        )

        for wl in self.__workload_commands:
            repr += textwrap.indent(
                f"* Collect feature regions for workload '{wl.command.label}'\n",
                (indent + 2) * " "
            )
        return repr

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> StepResult:
        # Create subfolder for the binary.
        tmp_dir = tmp_dir / self.__binary.name
        tmp_dir.mkdir(parents=True, exist_ok=True)

        with local.cwd(self.project.builddir):
            for prj_command in self.__workload_commands:
                print(f"Running workload:  {prj_command.command.label}")
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "feature_intensity",
                    prj_command.command,
                    file_suffix=".json"
                )

                print(f"{run_report_name=}")

                with cleanup(prj_command):
                    # noinspection PyStatementEffect
                    with local.env(VARA_TRACE_FILE=run_report_name):
                        (pb_cmd)()

        return actions.StepResult.OK


class WorkloadFeatureIntensityExperiment(FeatureExperiment, shorthand="WFI"):
    NAME = "WorkloadFeatureIntensity"
    DESCRIPTION = "Collects feature intensity data for all project example workloads."

    REPORT_SPEC = ReportSpecification(WorkloadFeatureIntensityReport)

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

        result_filepath = ReportFilepath(
            get_varats_result_folder(project),
            ReportFilename.get_file_name(
                self.shorthand(),
                self.report_spec().main_report.shorthand(), project.name, "all",
                ShortCommitHash(project.version_of_primary),
                str(project.run_uuid), FileStatusExtension.SUCCESS,
                self.REPORT_SPEC.main_report.file_type(),
                get_current_config_id(project)
            )
        )

        print(result_filepath.full_path())

        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    WorkloadFeatureRegions(project=project, binary=binary)
                    for binary in select_project_binaries(project)
                ]
            )
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

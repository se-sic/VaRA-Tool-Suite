"""Implements an experiment that times the execution of all project binaries."""

import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.project import Project
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.massif_report import MassIfAggregate
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


def _select_binaries(project: VProject):
    if project.name == "FastDownward":
        return [bi for bi in project.binaries if bi.name == "downward"][0]

    return project.binaries[0]


class HeapTrackStep(OutputFolderStep):
    """Times the execution of all project example workloads."""

    NAME = "HeapTrack"
    DESCRIPTION = "Measures heap usage of workloads using heaptrack."

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Only create a report file."""

        with local.cwd(self.project.builddir):
            for prj_command in workload_commands(
                self.project,
                self.__binary,
                [
                    WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL,
                    WorkloadCategory.MEDIUM
                ],
            ):

                heaptrack_cmd = local["heaptrack"]
                ht_print = local["heaptrack_print"]

                tmp_ht_output: Path = self.project.builddir / f"{prj_command.command.label}"

                ht_record = heaptrack_cmd["--raw", "--output", tmp_ht_output]
                ht_interpret = heaptrack_cmd[
                    "--interpret",
                    tmp_ht_output.with_suffix(".raw.zst")]

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "heaptrack", prj_command.command, self.__num, ".massif"
                )

                ht_print = ht_print["-M", run_report_name, "--file",
                                    tmp_ht_output.with_suffix(".zst")]

                with cleanup(prj_command):
                    pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                        ht_record, project=self.project
                    )
                    pb_cmd(retcode=self.__binary.valid_exit_codes)
                    bb.watch(ht_interpret)()
                    bb.watch(ht_print)()

        return actions.StepResult.OK


class HeapTrackExperiment(VersionExperiment, shorthand="HTE"):
    """Generates time report files."""

    NAME = "HeapTrack"

    REPORT_SPEC = ReportSpecification(MassIfAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        # Only consider the main/first binary
        binary = _select_binaries(project)

        measurement_repetitions = 1
        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report,
            project,
            binary,
            config_id=get_current_config_id(project),
        )

        analysis_actions = [
            actions.Compile(project),
            ZippedExperimentSteps(
                result_filepath, [
                    HeapTrackStep(project, rep_num, binary)
                    for rep_num in range(0, measurement_repetitions)
                ]
            ),
            actions.Clean(project)
        ]

        return analysis_actions

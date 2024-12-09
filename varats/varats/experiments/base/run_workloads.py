import textwrap
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from plumbum import local

from varats.experiment.experiment_util import get_default_compile_error_wrapped, \
    get_config_patch_steps, ZippedExperimentSteps, create_new_success_result_filepath, OutputFolderStep, \
    ZippedReportFolder
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.workload_util import WorkloadSpecificReportAggregate, workload_commands, \
    create_workload_specific_filename, WorkloadCategory
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportSpecification, ReportAggregate, FileStatusExtension
from varats.utils.git_util import ShortCommitHash

class RunAllWorkloads(OutputFolderStep):
    NAME = "RunAllWorkloads"
    DESCRIPTION = "Run all workloads of a project for a specific binary."

    project: VProject

    def __init__(self, project: VProject, binary: ProjectBinaryWrapper, experiment: FeatureExperiment, repetitions: int, file_name: str) -> None:
        super().__init__(project=project)
        self.__repetitions = repetitions
        self.__binary = binary
        self.__experiment = experiment
        self.__file_name = file_name

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run all workload for binary {self.__binary.name} ({self.__repetitions} repetitions)",
            indent * ' '
        )

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        with local.cwd(self.project.builddir):
            zip_tmp_dir = tmp_dir / self.__file_name

            wla_name_base = SimpleWLAggregate.get_file_name(
                self.__experiment.shorthand(), self.project.name, self.__binary.name,
                ShortCommitHash(self.project.version_of_primary), str(self.project.run_uuid),
                FileStatusExtension.SUCCESS, None
            )

            with ZippedReportFolder(zip_tmp_dir) as binary_report_folder:
                for prj_command in workload_commands(
                        self.project, self.__binary, [WorkloadCategory.EXAMPLE]
                ):
                    pb_cmd = prj_command.command.as_plumbum(project=self.project)

                    # Create report name for workload aggregate
                    wla_name = create_workload_specific_filename(wla_name_base.filename[:-4], prj_command.command, None, ".zip")

                    wla_zip = Path(binary_report_folder) / wla_name

                    with ZippedReportFolder(wla_zip) as workload_report_folder:
                        for i in range(self.__repetitions):
                            run_report_name = workload_report_folder / create_workload_specific_filename("text_report", prj_command.command, i, ".txt")

                            with cleanup(prj_command):
                                (pb_cmd > str(run_report_name))()

        return actions.StepResult.OK

class SimpleWLAggregate(WorkloadSpecificReportAggregate[BaseReport], shorthand="WLA", file_type=".zip"):
    """Simple workload report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, BaseReport)

class MultiWLAggregate(ReportAggregate[SimpleWLAggregate], shorthand="MWLA", file_type=".zip"):
    """Multi-workload report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, SimpleWLAggregate)

class MPRBinAggregate(MultiPatchReport[MultiWLAggregate], shorthand="MPBA", file_type=".zip"):
    """Multi-patch report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, MultiWLAggregate)

class RunWorkloads(FeatureExperiment, shorthand="RWL"):
    """ Runs executable workloads of a project.

        The idea of this experiment is to have a generic wrapper that just runs
        all workloads of a project for a specified amount of repetitions.
        The reports for each individual workload are simple text files that
        contain the output of the workload execution.
        This can then be used for simple data analyses and visualizations.

        This experiment is patch-aware and will run the workloads for each patch
        available for the respective revision of the project.

        The report structure is therefore a bit nested:
        - The main report is a MultiPatchReport that contains the reports for
            each patch.
        - Each patch report is a WorkloadSpecificReportAggregate that contains
            the reports for each workload.
    """

    NAME = "RunWorkloads"
    NUM_REPETITIONS = 3

    REPORT_SPEC = ReportSpecification(MPRBinAggregate)

    def actions_for_project(self, project):
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

        result_paths = dict()

        for binary in project.binaries:
            result_paths[binary.name] = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )

        fake_binary = ProjectBinaryWrapper("AllBinaries", None, BinaryType.EXECUTABLE)

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, fake_binary
        )

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )

        patch_steps = []
        for patch in patches:
            patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.extend(
                [ RunAllWorkloads(
                    project, binary, self, self.NUM_REPETITIONS,
                    file_name=MPRBinAggregate.create_patched_report_name(patch, binary.name)
                ) for binary in project.binaries ]
            )
            patch_steps.append(RevertPatch(project, patch))

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath,
                [
                    RunAllWorkloads(
                        project, binary, self, self.NUM_REPETITIONS,
                        file_name=MPRBinAggregate.create_baseline_report_name(binary.name)
                    ) for binary in project.binaries
                ] + patch_steps
            )
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions
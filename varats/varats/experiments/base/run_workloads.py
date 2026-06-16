import subprocess
import textwrap
from pathlib import Path

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from plumbum import local

from varats.experiment.experiment_util import (
    OutputFolderStep,
    ZippedExperimentSteps,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_config_patch_steps,
    get_default_compile_error_wrapped, create_stable_success_result_filepath, get_config_reverse_patch_steps,
)
from varats.experiment.steps.combinators import IfThenElse, AlwaysOk
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.workload_util import (
    WorkloadCategory,
    WorkloadSpecificReportAggregate,
    create_workload_specific_filename,
    workload_commands,
)
from varats.experiments.hidden_config.hidden_config_utils import (
    get_variations_as_dict, sample_variations,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.hidden_configurability_experiments import (
    filter_workloads,
    get_project_binaries, TimePatchedWorkloadsStep,
)
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import Patch, PatchProvider
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport, ReportSpecification
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash


class RunAllWorkloads(OutputFolderStep):
    NAME = "RunAllWorkloads"
    DESCRIPTION = "Run all workloads of a project for a specific binary."

    project: VProject

    def __init__(
        self, project: VProject, binary: ProjectBinaryWrapper,
        repetitions: int, file_name: str
    ) -> None:
        super().__init__(project=project)
        self.__repetitions = repetitions
        self.__binary = binary
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

            with ZippedReportFolder(zip_tmp_dir) as binary_report_folder:
                for prj_command in filter_workloads(self.project,self.__binary):
                    pb_cmd = prj_command.command.as_plumbum(
                        project=self.project
                    )

                    for i in range(self.__repetitions):
                        print(f"Running {prj_command.command.label}...")

                        run_report_name = binary_report_folder / create_workload_specific_filename(
                            "text-report", prj_command.command, i, ".txt"
                        )

                        with cleanup(prj_command):
                            (pb_cmd > str(run_report_name))(stderr=subprocess.STDOUT)

        return actions.StepResult.OK


class MultiWLAggregate(
    WorkloadSpecificReportAggregate[BaseReport],
    shorthand="MWLA",
    file_type=".zip"
):
    """Multi-workload report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, BaseReport)


class MPRBinAggregate(
    MultiPatchReport[MultiWLAggregate], shorthand="MPBA", file_type=".zip"
):
    """Multi-patch report aggregate."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, MultiWLAggregate)


class RunPatchedWorkloads(FeatureExperiment, shorthand="RPWL"):
    """
    Runs executable workloads of a project.

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

    NAME = "RunPatchedWorkloads"
    PATCH_TAG = "hidden-config"
    NUM_REPETITIONS = 2

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

        fake_binary = ProjectBinaryWrapper(
            "AllBinaries", None, BinaryType.EXECUTABLE
        )

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report,
            project,
            fake_binary,
            config_id=get_current_config_id(project),
        )

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )[self.PATCH_TAG]

        analysis_actions = get_config_patch_steps(project)
        variations = get_variations_as_dict(project)

        zipped_steps = []

        if len(variations) == 0:
            # Baseline step, test normal program behavior without any patch applied
            analysis_actions.append(actions.Compile(project))

            zipped_steps.extend(
                [
                    RunAllWorkloads(
                        project,
                        binary,
                        file_name=MPRBinAggregate.create_baseline_report_name(
                            binary.name
                        )
                                  + ".zip",
                        repetitions=self.NUM_REPETITIONS,
                    )
                    for binary in get_project_binaries(project)
                ]
            )
        else:
            # Filter patches based on the variations specified in the configuration
            patches_filtered: list[Patch] = [
                patch for patch in patches if patch.shortname in variations
            ]

            if len(patches_filtered) == 0:
                print(f"No patch found with shortname {[variations.keys()]}.")
                print(
                    f"Available patches: {[patch.shortname for patch in patches]}"
                )

            for patch in patches_filtered:
                patch_variations = variations[patch.shortname]

                if len(patch_variations) != 1:
                    print(
                        f"Warning: Patch '{patch.shortname}' defines more than one argument. This is not supported currently. Skipping this patch."
                    )
                    continue
                arg_name = next(iter(patch_variations))
                values: list[int] = list(patch_variations[arg_name])

                if arg_name not in patch.arguments:
                    print(
                        f"Warning: Patch '{patch.shortname}' does not define argument '{arg_name}'."
                    )
                    print(f"Available arguments: {patch.arguments}")
                    continue

                num_samples = 20
                values.extend(sample_variations(values, num_samples))

                for value in values:
                    zipped_steps.append(
                        ApplyPatch(project, patch, **{arg_name: value})
                    )

                    if len(zipped_steps) == 1:
                        # First iteration, perform a full compile
                        condition = actions.Compile(project)
                    else:
                        condition = ReCompile(project)

                    for b in get_project_binaries(project):
                        zipped_steps.append(
                            IfThenElse(
                                project,
                                condition=condition,
                                then_step=AlwaysOk(
                                    RunAllWorkloads(
                                        project,
                                        b,
                                        self.NUM_REPETITIONS,
                                        file_name=MPRBinAggregate.
                                                  create_patched_report_name(
                                            patch, b.name, **{arg_name: value}
                                        ) + ".zip"
                                    )
                                ),
                            )
                        )

                    zipped_steps.append(
                        RevertPatch(project, patch, **{arg_name: value})
                    )

        fake_binary = ProjectBinaryWrapper("ALL", Path(), BinaryType.EXECUTABLE)
        result_filepath = create_stable_success_result_filepath(
            self.get_handle(),
            MPRBinAggregate,
            project,
            fake_binary,
            get_current_config_id(project),
        )

        analysis_actions.append(
            ZippedExperimentSteps(result_filepath, zipped_steps)
        )

        analysis_actions.extend(get_config_reverse_patch_steps(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

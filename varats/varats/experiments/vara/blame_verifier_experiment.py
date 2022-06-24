"""
Implements the BlameVerifier experiment.

The experiment analyses a project, which contains llvm-debug-information and
checks for inconsistencies between VaRA-commit-hashes and debug-commit-hashes in
order to generate a BlameVerifierReport.
"""

import typing as tp

from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt, timeout

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportOpt as BVR_Opt,
)
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOptTBAA as BVR_NoOptTBAA,
)
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    get_varats_result_folder,
    ExperimentHandle,
    VersionExperiment,
    PEErrorHandler,
    create_new_success_result_filename,
    create_new_failed_result_filename,
)
from varats.experiment.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.report.report import ReportSpecification


class BlameVerifierReportGeneration(actions.Step):  # type: ignore
    """Analyse a project with the BlameVerifier and generate a
    BlameVerifierReport."""

    NAME = "BlameVerifierReportGeneration"
    DESCRIPTION = "Compares and analyses VaRA-commit-hashes with " \
                  "debug-commit-hashes."

    def __init__(
        self, project: Project, bc_file_extensions: tp.List[BCFileExtensions],
        experiment_handle: ExperimentHandle
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.bc_file_extensions = bc_file_extensions
        self.__experiment_handle = experiment_handle

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.

        Flags used:
            * -vara-BD: activates Blame Detection
            * -vara-init-commits: let's the Blame Detection initialize
            Commits for Repos
            * -vara-verify-blameMD: activate BlameMDVerifier
            * -vara-verifier-options=: chooses between multiple print options
                * Status: prints if the module as a whole passed or failed
        """
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = get_varats_result_folder(project)

        timeout_duration = '8h'

        for binary in project.binaries:
            bc_target_file = get_cached_bc_file_path(
                project, binary, self.bc_file_extensions
            )

            # Define empty success file.
            result_file = create_new_success_result_filename(
                self.__experiment_handle,
                self.__experiment_handle.report_spec().main_report, project,
                binary
            )

            # Define output file name of failed runs
            error_file = create_new_failed_result_filename(
                self.__experiment_handle,
                self.__experiment_handle.report_spec().main_report, project,
                binary
            )

            # Put together the path to the bc file and the opt command of vara
            vara_run_cmd = opt["-vara-BD", "-vara-init-commits",
                               "-vara-verify-blameMD",
                               "-vara-verifier-options=All",
                               str(bc_target_file), "-o", "/dev/null"]

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, vara_run_cmd] >
                f"{vara_result_folder}/{result_file}",
                PEErrorHandler(
                    vara_result_folder, error_file.filename, timeout_duration
                )
            )

        return actions.StepResult.OK


class BlameVerifierReportExperiment(VersionExperiment, shorthand="BVRE"):
    """BlameVerifierReportExperiment generalizes the implementation and usage
    over different optimization levels."""

    REPORT_SPEC = ReportSpecification()

    def __init__(
        self,
        project: Project,
        opt_flags: tp.Union[str, tp.List[str]],
        bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None
    ) -> None:
        super().__init__()

        if bc_file_extensions is None:
            bc_file_extensions = []

        self.projects = project
        self.__opt_flag = opt_flags
        self.__bc_file_extensions = bc_file_extensions

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        BE.setup_basic_blame_experiment(
            self, project,
            self.get_handle().report_spec().main_report
        )

        project.cflags.append('-g')
        project.cflags.append(self.__opt_flag)

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project, self.__bc_file_extensions
        )

        analysis_actions.append(
            BlameVerifierReportGeneration(
                project, self.__bc_file_extensions, self.get_handle()
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class BlameVerifierReportExperimentOpt(
    BlameVerifierReportExperiment, shorthand="BVRE_Opt"
):
    """Generates a Blame Verifier Report of the project(s) specified in the call
    with optimization (BVR_Opt)."""

    NAME = "GenerateBlameVerifierReportOpt"

    REPORT_SPEC = ReportSpecification(BVR_Opt)

    def __init__(self, projects: Project) -> None:
        super().__init__(
            projects, '-O2', [
                BCFileExtensions.DEBUG, BCFileExtensions.OPT,
                BCFileExtensions.BLAME
            ]
        )


class BlameVerifierReportExperimentNoOptTBAA(
    BlameVerifierReportExperiment, shorthand="BVRE_NoOptTBAA"
):
    """Generates a Blame Verifier Report of the project(s) specified in the call
    without any optimization and TBAA metadata (BVR_NoOptTBAA)."""

    NAME = "GenerateBlameVerifierReportNoOptTBAA"

    REPORT_SPEC = ReportSpecification(BVR_NoOptTBAA)

    def __init__(self, projects: Project) -> None:
        super().__init__(
            projects, ["-O1", "-Xclang", "-disable-llvm-optzns"], [
                BCFileExtensions.DEBUG, BCFileExtensions.NO_OPT,
                BCFileExtensions.TBAA, BCFileExtensions.BLAME
            ]
        )

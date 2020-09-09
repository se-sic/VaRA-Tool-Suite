"""
Implements the BlameVerifier experiment.

The experiment analyses a project, which contains llvm-debug-information and
checks for inconsistencies between VaRA-commit-hashes and debug-commit-hashes in
order to generate a BlameVerifierReport.
"""

import typing as tp

import benchbuild.utils.actions as actions
from benchbuild.project import Project
from benchbuild.utils.cmd import opt, mkdir, timeout
from plumbum import local

import varats.experiments.vara.blame_experiment as BE
from varats.data.report import FileStatusExtension as FSE
from varats.data.report import BaseReport
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt as BVR_NoOpt,
)
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportOpt as BVR_Opt,
)
from varats.experiments.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    PEErrorHandler,
)
from varats.utils.settings import bb_cfg


class BlameVerifierReportGeneration(actions.Step):  # type: ignore
    """Analyse a project with the BlameVerifier and generate a
    BlameVerifierReport."""

    NAME = "BlameVerifierReportGeneration"
    DESCRIPTION = "Compares and analyses VaRA-commit-hashes with " \
                  "debug-commit-hashes."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self, project: Project, bc_file_extensions: tp.List[BCFileExtensions],
        report_type: tp.Type[BaseReport]
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.bc_file_extensions = bc_file_extensions
        self.report_type = report_type

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
            return
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", vara_result_folder)

        timeout_duration = '8h'

        for binary in project.binaries:
            bc_target_file = get_cached_bc_file_path(project, binary)

            # Define empty success file.
            result_file = self.report_type.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success,
                file_ext=".txt"
            )

            # Define output file name of failed runs
            error_file = self.report_type.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Failed,
                file_ext=".txt"
            )

            # Put together the path to the bc file and the opt command of vara
            vara_run_cmd = opt["-vara-BD", "-vara-init-commits",
                               "-vara-verify-blameMD",
                               "-vara-verifier-options=All",
                               str(bc_target_file), "-o", "/dev/null"]

            exec_func_with_pe_error_handler(
                timeout[timeout_duration,
                        vara_run_cmd] > "{res_folder}/{res_file}".
                format(res_folder=vara_result_folder, res_file=result_file),
                PEErrorHandler(
                    vara_result_folder, error_file, timeout_duration
                )
            )


class BlameVerifierReportExperiment(VersionExperiment):
    """BlameVerifierReportExperiment generalizes the implementation and usage
    over different optimization levels."""

    def __init__(
        self,
        project: Project,
        opt_flag: str,
        report_type: tp.Type[BaseReport],
        bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None
    ) -> None:
        super().__init__()

        if bc_file_extensions is None:
            bc_file_extensions = []

        self.projects = project
        self.__opt_flag = opt_flag
        self.__bc_file_extensions = bc_file_extensions
        self.__report_type = report_type

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        BE.setup_basic_blame_experiment(
            self, project, self.__report_type,
            BlameVerifierReportGeneration.RESULT_FOLDER_TEMPLATE
        )

        project.cflags.append('-g')
        project.cflags.append(self.__opt_flag)

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project, self.__bc_file_extensions
        )

        analysis_actions.append(
            BlameVerifierReportGeneration(
                project, self.__bc_file_extensions, self.__report_type
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class BlameVerifierReportExperimentNoOpt(BlameVerifierReportExperiment):
    """Generates a Blame Verifier Report of the project(s) specified in the call
    without any optimization (BVR_NoOpt)."""

    NAME = "GenerateBlameVerifierReportNoOpt"

    REPORT_TYPE = BVR_NoOpt

    def __init__(self, projects: Project) -> None:
        super().__init__(
            projects, '-O0', BVR_NoOpt,
            [BCFileExtensions.DEBUG, BCFileExtensions.NO_OPT]
        )


class BlameVerifierReportExperimentOpt(BlameVerifierReportExperiment):
    """Generates a Blame Verifier Report of the project(s) specified in the call
    with optimization (BVR_Opt)."""

    NAME = "GenerateBlameVerifierReportOpt"

    REPORT_TYPE = BVR_Opt

    def __init__(self, projects: Project) -> None:
        super().__init__(
            projects, '-O2', BVR_Opt,
            [BCFileExtensions.DEBUG, BCFileExtensions.OPT]
        )

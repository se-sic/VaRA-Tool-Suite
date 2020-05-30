"""
Implements the BlameVerifier experiment.

The experiment analyses a project, which contains llvm-debug-information and
checks for inconsistencies between VaRA-commit-hashes and debug-commit-hashes in
order to generate a BlameVerifierReport.
"""

import typing as tp

import benchbuild.utils.actions as actions
from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import opt, mkdir, timeout
from plumbum import local

import varats.experiments.blame_experiment as BE
from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt as BVR_NoOpt,
)
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportOpt as BVR_Opt,
)
from varats.experiments.wllvm import BCFileExtensions, Extract
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    PEErrorHandler,
)


class BlameVerifierReportGeneration(actions.Step):  # type: ignore
    """Analyse a project with the BlameVerifier and generate a
    BlameVerifierReport."""

    NAME = "BlameVerifierReportGeneration"
    DESCRIPTION = "Compares and analyses VaRA-commit-hashes with " \
                  "debug-commit-hashes."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self, project: Project, bc_file_extensions: tp.List[BCFileExtensions]
    ):
        super(BlameVerifierReportGeneration,
              self).__init__(obj=project, action_fn=self.analyze)
        self.bc_file_extensions = bc_file_extensions

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
            * -vara-report-outfile=<path>: specify the path to store the results
        """
        if not self.obj:
            return
        project = self.obj

        bc_cache_folder = local.path(
            Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                cache_dir=str(BB_CFG["varats"]["result"]),
                project_name=str(project.name)
            )
        )

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(BB_CFG["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", vara_result_folder)

        for binary in project.binaries:
            result_file = BVR_NoOpt.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            opt_params = [
                "-vara-BD", "-vara-init-commits", "-vara-verify-blameMD",
                "-vara-verifier-options=Status",
                "-vara-report-outfile={res_folder}/{res_file}".format(
                    res_folder=vara_result_folder, res_file=result_file
                )
            ]

            opt_params.append(
                bc_cache_folder / Extract.get_bc_file_name(
                    project_name=project.name,
                    binary_name=binary.name,
                    project_version=project.version,
                    bc_file_extensions=self.bc_file_extensions
                )
            )

            run_cmd = opt[opt_params]

            timeout_duration = '8h'

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                PEErrorHandler(
                    vara_result_folder,
                    BVR_NoOpt.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=str(project.version),
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed,
                        file_ext=".txt"
                    ), timeout_duration
                )
            )


class BlameVerifierReportExperiment(VersionExperiment):
    """
    BlameVerifierReportExperiment generalizes the implementation and usage over different
    optimization levels.

    Only its subclasses should be instantiated.
    """

    def __init__(
        self,
        project,
        opt_flag,
        report_type,
        bc_file_extensions: tp.List[BCFileExtensions] = []
    ) -> None:
        super().__init__()
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
            BlameVerifierReportGeneration(project, self.__bc_file_extensions)
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

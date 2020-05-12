"""
Implements the BlameVerifier experiment.

The experiment analyses a project, which contains llvm-debug-information and
checks for inconsistencies between VaRA-commit-hashes and debug-commit-hashes in
order to generate a BlameVerifierReport.
"""

import typing as tp
from abc import abstractmethod

import benchbuild.utils.actions as actions
from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import opt, mkdir, timeout
from plumbum import local

import varats.experiments.blame_experiment as BE
from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.blame_verifier_report import BlameVerifierReport as BVR
from varats.experiments.wllvm import Extensions, Extract
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    PEErrorHandler,
)


class BlameVerifierReportGeneration(actions.Step):  # type: ignore
    """Analyse a project with the BlameVerifier and generate a
    BlameVerifierReport."""

    NAME = "BlameVerifierReportGeneration"
    DESCRIPTION = "Compares and analyses VaRA-commit-hashes and " \
                  "debug-commit-hashes."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project, extensions: list):
        super(BlameVerifierReportGeneration,
              self).__init__(obj=project, action_fn=self.analyze)
        self.extensions = extensions

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
            result_file = BVR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            opt_params = [
                "-vara-BD", "-vara-init-commits", "-vara-verify-blameMD",
                "-vara-verifier-options=Status".format(
                    res_folder=vara_result_folder, res_file=result_file
                )
            ]

            opt_params.append(
                bc_cache_folder / Extract.get_bc_file_name(
                    project_name=project.name,
                    binary_name=binary.name,
                    project_version=project.version,
                    extensions=self.extensions
                )
            )

            run_cmd = opt[opt_params]

            timeout_duration = '8h'

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                PEErrorHandler(
                    vara_result_folder,
                    BVR.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=str(project.version),
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed,
                        file_ext=".txt"
                    ), run_cmd, timeout_duration
                )
            )


class BlameVerifierReportExperiment(VersionExperiment):
    """Abstract Blame Verifier Report used for different optimization levels in
    the compilation."""

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        pass


class BlameVerifierReportExperimentNoOpt(BlameVerifierReportExperiment):
    """Generates a Blame Verifier Report (BVR) of the project(s) specified in
    the call without any optimization."""

    NAME = "GenerateBlameVerifierReportNoOpt"

    REPORT_TYPE = BVR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        extensions = [Extensions.DEBUG, Extensions.NO_OPT]

        BE.setup_basic_blame_experiment(
            self, project, BVR,
            BlameVerifierReportGeneration.RESULT_FOLDER_TEMPLATE
        )
        project.cflags.append("-g")
        project.cflags.append("-O0")

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project, extensions
        )

        analysis_actions.append(
            BlameVerifierReportGeneration(project, extensions)
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class BlameVerifierReportExperimentOpt(BlameVerifierReportExperiment):
    """Generates a Blame Verifier Report (BVR) of the project(s) specified in
    the call with optimization."""

    NAME = "GenerateBlameVerifierReportOpt"

    REPORT_TYPE = BVR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        extensions = [Extensions.DEBUG, Extensions.OPT]

        BE.setup_basic_blame_experiment(
            self, project, BVR,
            BlameVerifierReportGeneration.RESULT_FOLDER_TEMPLATE
        )
        project.cflags.append("-g")
        project.cflags.append("-O2")

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project, extensions
        )

        analysis_actions.append(
            BlameVerifierReportGeneration(project, extensions)
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

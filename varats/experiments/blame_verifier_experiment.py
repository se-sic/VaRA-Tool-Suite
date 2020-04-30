"""
Implements the BlameVerifier experiment. The experiment analyses a project,
which contains llvm-debug-information and checks for inconsistencies between
VaRA-commit-hashes and debug-commit-hashes in order to generate a
BlameVerifierReport.
"""

import typing as tp

from benchbuild import project
from plumbum import local

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import opt, mkdir, timeout

from varats.data.reports.blame_verifier_report import BlameVerifierReport as BVR
import varats.experiments.blame_experiment as BE
from varats.data.report import FileStatusExtension as FSE
from varats.experiments.wllvm import Extract
from varats.utils.experiment_util import (exec_func_with_pe_error_handler,
                                          VersionExperiment, PEErrorHandler)


class BlameVerifierReportGeneration(actions.Step):  # type: ignore
    """
    Analyse a project with the BlameVerifier and generate a BlameVerifierReport.
    """

    NAME = "BlameVerifierReportGeneration"
    DESCRIPTION = "Compares and analyses VaRA-commit-hashes and " \
                  "debug-commit-hashes."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
            self,
            project: Project
    ):
        super(BlameVerifierReportGeneration, self).__init__(
            obj=project,
            action_fn=self.analyze
        )

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
                project_name=str(project.name)))

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(BB_CFG["varats"]["outfile"]),
            project_dir=str(project.name))

        mkdir("-p", vara_result_folder)

        for binary in project.binaries:
            result_file = BVR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            opt_params = [
                "-vara-BD", "-vara-init-commits",
                "-vara-verify-blameMD", "-vara-verifier-options=Status".format(
                    res_folder=vara_result_folder, res_file=result_file)
            ]

            opt_params.append(bc_cache_folder / Extract.get_bc_file_name(
                project_name=project.name,
                binary_name=binary.name,
                project_version=project.version,
                dbg=True))

            run_cmd = opt[opt_params]

            timeout_duration = '8h'

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                PEErrorHandler(
                    vara_result_folder,
                    BVR.get_file_name(project_name=str(project.name),
                                      binary_name=binary.name,
                                      project_version=str(project.version),
                                      project_uuid=str(project.run_uuid),
                                      extension_type=FSE.Failed,
                                      file_ext=".txt"), run_cmd,
                    timeout_duration))


class BlameVerifierReportExperiment(VersionExperiment):
    """
    Generates a Blame Verifier Report (BVR) of the project(s) specified in the
    call.
    """

    NAME = "GenerateBlameVerifierReport"

    REPORT_TYPE = BVR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in
        the call in a fixed order.
        """

        BE.setup_basic_blame_experiment(
            self, project, BVR,
            BlameVerifierReportGeneration.RESULT_FOLDER_TEMPLATE)
        project.cflags.append("-g")

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project, True)

        analysis_actions.append(BlameVerifierReportGeneration(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

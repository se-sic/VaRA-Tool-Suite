"""
Implements the basic blame report experiment. The experiment analyses a project
with VaRA's blame analysis and generates a BlameReport.
"""

import typing as tp

from plumbum import local

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import opt, mkdir

from varats.experiments.wllvm import Extract
import varats.experiments.blame_experiment as BE
from varats.data.reports.blame_report import BlameReport as BR
from varats.data.report import FileStatusExtension as FSE
from varats.utils.experiment_util import (exec_func_with_pe_error_handler,
                                          VersionExperiment, PEErrorHandler)


class BlameReportGeneration(actions.Step):  # type: ignore
    """
    Analyse a project with VaRA and generate a BlameReport.
    """

    NAME = "BlameReportGeneration"
    DESCRIPTION = "Analyses the bitcode with -vara-BR of VaRA."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self,
        project: Project,
    ):
        super(BlameReportGeneration, self).__init__(obj=project,
                                                    action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.

        Flags used:
            * -vara-BR: to run a commit flow report
            * -yaml-report-outfile=<path>: specify the path to store the results
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
            result_file = BR.get_file_name(project_name=str(project.name),
                                           binary_name=binary.name,
                                           project_version=str(project.version),
                                           project_uuid=str(project.run_uuid),
                                           extension_type=FSE.Success)

            opt_params = [
                "-vara-BD", "-vara-BR", "-vara-init-commits",
                "-vara-report-outfile={res_folder}/{res_file}".format(
                    res_folder=vara_result_folder, res_file=result_file)
            ]

            opt_params.append(bc_cache_folder / Extract.BC_FILE_TEMPLATE.format(
                project_name=project.name,
                binary_name=binary.name,
                project_version=project.version))

            run_cmd = opt[opt_params]

            timeout_duration = '8h'
            from benchbuild.utils.cmd import timeout

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                PEErrorHandler(
                    vara_result_folder,
                    BR.get_file_name(project_name=str(project.name),
                                     binary_name=binary.name,
                                     project_version=str(project.version),
                                     project_uuid=str(project.run_uuid),
                                     extension_type=FSE.Failed,
                                     file_ext=".txt"), run_cmd,
                    timeout_duration))


class BlameReportExperiment(VersionExperiment):
    """
    Generates a commit flow report (CFR) of the project(s) specified in the
    call.
    """

    NAME = "GenerateBlameReport"

    REPORT_TYPE = BR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in
        the call in a fixed order.

        Args:
            project: to analyze
        """

        BE.setup_basic_blame_experiment(
            self, project, BR, BlameReportGeneration.RESULT_FOLDER_TEMPLATE)

        analysis_actions = BE.generate_basic_blame_experiment_actions(project)

        analysis_actions.append(BlameReportGeneration(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""

import typing as tp
import random
from os import path
from pathlib import Path

from plumbum import local
from plumbum.commands import ProcessExecutionError
from plumbum.commands.base import BoundCommand

from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt, mkdir
import benchbuild.utils.actions as actions

from varats.data.reports.commit_report import CommitReport as CR
from varats.data.report import FileStatusExtension as FSE
from varats.data.revisions import get_proccessed_revisions
from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM
from varats.settings import CFG as V_CFG
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler, FunctionPEErrorWrapper,
    VaRAVersionExperiment, PEErrorHandler)


class CFRAnalysis(actions.Step):  # type: ignore
    """
    Analyse a project with VaRA and generate a Commit-Flow Report.
    """

    NAME = "CFRAnalysis"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    INTERACTION_FILTER_TEMPLATE = "InteractionFilter-{experiment}-{project}.yaml"

    def __init__(self,
                 project: Project,
                 interaction_filter_experiment_name: tp.Optional[str] = None):
        super(CFRAnalysis, self).__init__(obj=project, action_fn=self.analyze)
        self.__interaction_filter_experiment_name = interaction_filter_experiment_name

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -vara-CFR: to run a commit flow report
            -yaml-out-file=<path>: specify the path to store the results
        """
        if not self.obj:
            return
        project = self.obj

        if self.__interaction_filter_experiment_name is None:
            interaction_filter_file = Path(
                self.INTERACTION_FILTER_TEMPLATE.format(
                    experiment="GitBlameAnnotationReport",
                    project=str(project.name)))
        else:
            interaction_filter_file = Path(
                self.INTERACTION_FILTER_TEMPLATE.format(
                    experiment=self.__interaction_filter_experiment_name,
                    project=str(project.name)))
            if not interaction_filter_file.is_file():
                raise Exception("Could not load interaction filter file \"" +
                                str(interaction_filter_file) + "\"")

        bc_cache_folder = local.path(Extract.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name)))

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(CFG["vara"]["outfile"]),
            project_dir=str(project.name))

        mkdir("-p", vara_result_folder)

        for binary_name in project.BIN_NAMES:
            result_file = CR.get_file_name(
                project_name=str(project.name),
                binary_name=binary_name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            opt_params = [
                "-vara-BD", "-vara-CFR", "-vara-init-commits",
                "-yaml-out-file={res_folder}/{res_file}".format(
                    res_folder=vara_result_folder, res_file=result_file)]

            if interaction_filter_file.is_file():
                opt_params.append("-vara-cf-interaction-filter={}".format(
                    str(interaction_filter_file)))

            opt_params.append(bc_cache_folder /
                              Extract.BC_FILE_TEMPLATE.format(
                                  project_name=project.name,
                                  binary_name=binary_name,
                                  project_version=project.version))

            run_cmd = opt(*opt_params)

            timeout_duration = '8h'
            from benchbuild.utils.cmd import timeout

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                PEErrorHandler(
                    vara_result_folder,
                    CR.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version),
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed), run_cmd, timeout_duration))


class GitBlameAnntotationReport(VaRAVersionExperiment):
    """
    Generates a commit flow report (CFR) of the project(s) specified in the
    call.
    """

    NAME = "GitBlameAnnotationReport"

    REPORT_TYPE = CR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in
        the call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step
        project.compile = FunctionPEErrorWrapper(
            project.compile,
            PEErrorHandler(
                CFRAnalysis.RESULT_FOLDER_TEMPLATE.format(
                    result_dir=str(CFG["vara"]["outfile"]),
                    project_dir=str(project.name)),
                CR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=str(project.version),
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError),
            ))

        # This c-flag is provided by VaRA and it suggests to use the git-blame
        # annotation.
        project.cflags = ["-fvara-GB"]

        analysis_actions = []

        # Check if all binaries have correspondong BC files
        all_files_present = True
        for binary_name in project.BIN_NAMES:
            all_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(CFG["vara"]["result"]),
                        project_name=str(project.name)) +
                    Extract.BC_FILE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version))))

        if not all_files_present:
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(CFRAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

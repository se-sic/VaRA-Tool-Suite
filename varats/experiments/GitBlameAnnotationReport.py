"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""
from os import path
from pathlib import Path

from plumbum import local

from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt, mkdir
import benchbuild.utils.actions as actions

from varats.experiments.Extract import Extract
from varats.experiments.Wllvm import RunWLLVM
from varats.settings import CFG as V_CFG
from varats.data.commit_report import CommitReport as CR


class CFRAnalysis(actions.Step):
    """
    Analyse a project with VaRA and generate a Commit-Flow Report.
    """

    NAME = "CFRAnalysis"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"
    RESULT_FILE_TEMPLATE = \
        "{project_name}-{project_version}_{project_uuid}.yaml"

    def __call__(self):
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -vara-CFR: to run a commit flow report
            -yaml-out-file=<path>: specify the path to store the results
        """
        if not self.obj:
            return
        project = self.obj

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

        result_file = self.RESULT_FILE_TEMPLATE.format(
            project_name=str(project.name),
            project_version=str(project.version),
            project_uuid=str(project.run_uuid))

        run_cmd = opt[
            "-vara-BD", "-vara-CFR", "-yaml-out-file={res_folder}/{res_file}"
            .format(res_folder=vara_result_folder, res_file=result_file),
            bc_cache_folder / project.name + "-" + project.version + ".bc"]
        run_cmd()


class GitBlameAnntotationReport(Experiment):
    """
    Generates a commit flow report (CFR) of the project(s) specified in the
    call.
    """

    NAME = "GitBlameAnnotationReport"

    def actions_for_project(self, project):
        """Returns the specified steps to run the project(s) specified in
        the call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # This c-flag is provided by VaRA and it suggests to use the git-blame
        # annotation.
        project.cflags = ["-fvara-GB"]

        analysis_actions = []
        if not path.exists(local.path(
                Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                    cache_dir=str(CFG["vara"]["result"]),
                    project_name=str(project.name)) +
                Extract.BC_FILE_TEMPLATE.format(
                    project_name=str(project.name),
                    project_version=str(project.version)))):

            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(CFRAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

    def sample(self, prj_cls, versions):
        """
        Adapt version sampling process if needed, otherwise fallback to default
        implementation.
        """
        if bool(V_CFG["experiment"]["only_missing"]):
            res_dir = Path("{result_folder}/{project_name}/"
                           .format(result_folder=V_CFG["result_dir"],
                                   project_name=str(prj_cls.NAME)))

            processed_version = []
            for res_file in res_dir.iterdir():
                if not str(res_file.stem).startswith(
                        "{}-".format(prj_cls.NAME)):
                    continue
                match = CR.FILE_NAME_REGEX.search(res_file.stem)
                processed_version.append(match.group("file_commit_hash"))

            versions = [vers for vers in prj_cls.versions()
                        if vers not in processed_version]
            if not versions:
                print("Could not find any unprocessed versions.")
                return

            head, *tail = versions
            yield head
            if bool(CFG["versions"]["full"]):
                for version in tail:
                    yield version
        else:
            for val in Experiment.sample(self, prj_cls, versions):
                yield val

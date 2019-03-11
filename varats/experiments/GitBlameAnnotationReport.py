"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""
from os import path

from plumbum import local

from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt
import benchbuild.utils.actions as actions

from varats.experiments.Extract import Extract
from varats.experiments.Wllvm import RunWLLVM


class CFRAnalysis(actions.Step):
    """
    Analyse a project with VaRA and generate a Commit-Flow Report.
    """

    NAME = "CFRAnalysis"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."

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

        project_src = local.path(str(CFG["vara"]["result"]))

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        outfile = "-yaml-out-file={}".format(
            str(CFG["vara"]["outfile"])) + "/" +\
            str(project.name) + "-" + str(project.version) + "_" +\
            str(project.run_uuid) + ".yaml"
        run_cmd = opt[
            "-vara-BD", "-vara-CFR", outfile, project_src / project.name +
            "-" + project.version + ".bc"]
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
                str(CFG["vara"]["result"].value)) / project.name + "-" +
                           project.version + ".bc"):
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(CFRAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""
from os import path

import benchbuild.utils.actions as actions
from benchbuild import extensions as ext
from benchbuild.experiment import Experiment
from benchbuild.extensions import RunCompiler, RuntimeExtension, RunWithTime
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt
from plumbum import local
from varats.experiments.Extract import Extract as Extract


class RunWLLVM(ext.Extension):
    """
    This extension implements the WLLVM compiler.

    This class is an extension that implements the WLLVM compiler with the
    required flags LLVM_COMPILER=clang and LLVM_OUTPUFILE=<path>. This compiler
    is used to transfer the complete project into LLVM-IR.
    """

    def __call__(self, command, *args, **kwargs):
        with local.env(LLVM_COMPILER="clang"):
            from benchbuild.utils.cmd import wllvm
            res = self.call_next(wllvm, *args, **kwargs)
        return res


class Analyse(actions.Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."


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
        project.runtime_extension = RuntimeExtension(project, self) \
                                    << ext.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = RunCompiler(project, self) \
                                     << RunWLLVM() \
                                     << ext.RunWithTimeout()

        # This c-flag is provided by VaRA and it suggests to use the git-blame
        # annotation.
        project.cflags = ["-fvara-GB"]

        def evaluate_analysis():
            """
            This step performs the actual analysis with the correct flags.
            Flags:
                -vara-CFR: to run a commit flow report
                -yaml-out-file=<path>: specify the path to store the results
            """
            project_src = CFG["vara"]["result"].value()

            # Add to the user-defined path for saving the results of the 
            # analysis also the name and the unique id of the project of every
            # run.
            outfile = "-yaml-out-file={}".format(
                CFG["vara"]["outfile"].value()) + "/" + str(
                project.name) + "-" + str(project.run_uuid) + ".yaml"
            run_cmd = opt["-vara-CFR", outfile, path.join(str(project_src),
                                                          project.name + ".bc")]
            run_cmd()

        analysis_actions = []
        if not path.exists(
                path.join(str(CFG["vara"]["result"].value()),
                          project.name + ".bc")):
            analysis_actions.append(actions.MakeBuildDir(project))
            analysis_actions.append(actions.Prepare(project))
            analysis_actions.append(actions.Download(project))
            analysis_actions.append(actions.Configure(project))
            analysis_actions.append(actions.Build(project))
            analysis_actions.append(actions.Run(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(Analyse(self, evaluate_analysis))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

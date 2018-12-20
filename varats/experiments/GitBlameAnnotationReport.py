"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""
import os

import benchbuild.utils.actions as actions

from os import getenv
from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time, base
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt
from benchbuild.utils.path import list_to_path
from benchbuild.utils.path import path_to_list
from plumbum import local
from varats.experiments.Extract import Extract as Extract


class RunWLLVM(base.Extension):
    """
    This extension implements the WLLVM compiler.

    This class is an extension that implements the WLLVM compiler with the
    required flags LLVM_COMPILER=clang and LLVM_OUTPUFILE=<path>. This compiler
    is used to transfer the complete project into LLVM-IR.
    """

    def __call__(self, cc, *args, **kwargs):
        if str(cc).endswith("clang++"):
            wllvm = local["wllvm++"]
        else:
            wllvm = local["wllvm"]

        env = CFG["env"].value
        path = path_to_list(getenv("PATH", ""))
        path.extend(env.get("PATH", []))

        libs_path = path_to_list(getenv("LD_LIBRARY_PATH", ""))
        libs_path.extend(env.get("LD_LIBRARY_PATH", []))

        wllvm = wllvm.with_env(LLVM_COMPILER="clang",
                               PATH=list_to_path(path),
                               LD_LIBRARY_PATH=list_to_path(libs_path))

        return self.call_next(wllvm, *args, **kwargs)


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
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

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
            project_src = local.path(str(CFG["vara"]["result"]))

            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            outfile = "-yaml-out-file={}".format(
                str(CFG["vara"]["outfile"])) + "/" +\
                str(project.name) + "-" + str(project.run_uuid) + ".yaml"
            run_cmd = opt[
                "-vara-CFR", outfile, project_src / project.name + ".bc"]
            run_cmd()

        analysis_actions = []
        if not os.path.exists(local.path(
                str(CFG["vara"]["result"].value)) / project.name + ".bc"):
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(Analyse(self, evaluate_analysis))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA).
For annotation we use the git-blame data of git.
"""
from benchbuild.experiment import Experiment
from benchbuild import extensions as ext
from benchbuild.extensions import RunWithTime, RuntimeExtension, RunCompiler
from benchbuild.settings import CFG
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import extract_bc, opt
from plumbum import local
from os import path

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


class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."


class Analyse(actions.Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."


class GitBlameAnntotation(Experiment):
    """
    Generates a commit flow report (CFR) of the project(s) specified in the
    call.
    """

    NAME = "GitBlameAnnotation"

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

        def evaluate_extraction():
            """
            This step extracts the bitcode of the executable of the project
            into one file.
            """
            project_src = path.join(project.builddir, project.src_dir)
            with local.cwd(project_src):
                extract_bc(project.name)

        def evaluate_analysis():
            """
            This step performs the actual analysis with the correct flags.
            Flags:
                -vara-CFR: to run a commit flow report
                -yaml-out-file=<path>: specify the path to store the results
            """
            project_src = path.join(project.builddir, project.src_dir)

            # Add to the user-defined path for saving the results of the 
            # analysis also the name and the unique id of the project of every
            # run.
            outfile = "-yaml-out-file={}".format(
                CFG["vara"]["outfile"].value()) + "/" + str(project.name) + \
                    "-" + str(project.run_uuid) + ".yaml"
            run_cmd = opt["-vara-CFR", outfile,
                          path.join(project_src, project.name + ".bc")]
            run_cmd()

        return [
            actions.MakeBuildDir(project),
            actions.Prepare(project),
            actions.Download(project),
            actions.Configure(project),
            actions.Build(project),
            actions.Run(project),
            Extract(self, evaluate_extraction),
            Analyse(self, evaluate_analysis),
            actions.Clean(project)
        ]

"""
TODO
"""
import os

from plumbum import local

from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt
import benchbuild.utils.actions as actions

from varats.experiments.Extract import Extract
from varats.experiments.Wllvm import RunWLLVM


class Analyse(actions.Step):
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses llvm bitcode with phasar."


class Phasar(Experiment):
    """
    Runs the default Phasar analysis on an project.
    """

    NAME = "Phasar"

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

        def evaluate_analysis():
            """
            This step performs the actual analysis.
            """
            project_src = local.path(str(CFG["vara"]["result"]))

            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            run_cmd = opt["-load",
                          "/home/vulder/git/phasar/build/dev/lib/PhasarPass" +
                          "/libphasar_passd.so", "-phasar", "--entry-points",
                          "main"]
            # TODO: refactor out direct loading of phasar lib
            run_cmd(project_src/project.name + ".bc")

        analysis_actions = []
        if not os.path.exists(local.path(
                str(CFG["vara"]["result"].value)) / project.name + ".bc"):
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(Analyse(self, evaluate_analysis))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

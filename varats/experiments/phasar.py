"""
Experiment module for phasa analyses.
"""

import typing as tp
import os

from plumbum import local

from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import opt
import benchbuild.utils.actions as actions

from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM


class DefaultAnalysis(actions.Step):  # type: ignore
    """
    Analyse a project with Phasar's default analysis.
    """
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses llvm bitcode with phasar."

    # TODO: refactor out direct loading of phasar lib
    PATH_TO_PHASAR_PASS_LIB = "/home/vulder/git/phasar/build/dev/lib/" +\
        "PhasarPass/libphasar_passd.so"

    def __call__(self) -> actions.Step:
        """
        This step performs the analysis.
        """
        if not self.obj:
            return
        project = self.obj

        project_src = local.path(str(CFG["vara"]["result"]))

        run_cmd = opt["-load", self.PATH_TO_PHASAR_PASS_LIB, "-phasar",
                      "--entry-points", "main"]

        run_cmd(project_src / project.name + ".bc")


class PhasarDefault(Experiment):  # type: ignore
    """
    Runs the default Phasar analysis on an project.
    """

    NAME = "PhasarDefault"

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

        analysis_actions = []
        if not os.path.exists(
                local.path(str(CFG["vara"]["result"].value)) / project.name +
                ".bc"):
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(DefaultAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

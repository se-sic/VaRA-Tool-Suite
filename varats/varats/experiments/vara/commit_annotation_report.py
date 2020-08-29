"""
Implements the commit-flow report with an annotation-script.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA). For annotation we use the annotation script by
Florian Niederhuber, which can be accessed via the site-packages folder due to
the installation via the Package manager pip.
"""

import os
import typing as tp

from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import Step
from benchbuild.utils.cmd import cp, extract_bc, opt
from plumbum import local

from varats.experiments.wllvm import RunWLLVM
# These two new config parameters are needed to include Niederhuber's prepare-
# script and to make the folder in which the results of the analyses are
# stored user-defined.
from varats.utils.settings import bb_cfg

bb_cfg()["varats"] = {
    "prepare": {
        "default": "",
        "desc": "Path to the prepare script of Niederhuber in VaRA"
    },
    "outfile": {
        "default": "",
        "desc": "Path to store results of VaRA CFR analysis."
    },
    "result": {
        "default": "missingPath/annotatedResults",
        "desc": "Path to store already annotated projects."
    }
}


class Prepare(Step):  # type: ignore
    """Benchbuild prepare step to setup projects for later analysis."""
    NAME = "PREPARE"
    DESCRIPTION = "Prepares the analysis by annotating the project with the \
        annotation-script of Florian Niederhuber that is provided through \
        prepare.sh."


class Extract(Step):  # type: ignore
    """Extract step to extract a llvm bitcode file (.bc) from the project."""
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."


class Analyse(Step):  # type: ignore
    """Analysis step to run vara's commit annotation report pass."""
    NAME = "ANALYSE"
    DESCRIPTION = "Analyses the bitcode with CFR of VaRA."


class CommitAnnotationReport(Experiment):  # type: ignore
    """Generates a commit flow report (CFR) of the project(s) specified in the
    call."""

    NAME = "CommitAnnotationReport"

    def actions_for_project(self, project: Project) -> tp.List[Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # This c-flag is provided by VaRA and it suggests to use the commit
        # annotation.
        project.cflags = ["-fvara-handleRM=Commit"]

        # Builds the path where the source code of the project is located.
        project_src = project.builddir / project.src_dir

        def evaluate_preparation() -> None:
            """
            This step annotates the project with the annotation script of
            Florian Niederhuber provided in the prepare-script (prepare.sh).

            prepare.sh can be accessed via the site-packages folder of all
            python packages installed via pip.
            """
            prepare = local["prepare.sh"]

            # Move the standard project source directory to the "out" folder,
            # created in the prepare script, to acces the annotated source
            # code.
            project.src_dir = project.src_dir / "out"

            with local.cwd(project_src):
                prepare(
                    "-c", str(bb_cfg()["env"]["path"][0]), "-t",
                    str(bb_cfg()["varats"]["prepare"].value)
                )

        def evaluate_extraction() -> None:
            """This step extracts the bitcode of the executable of the project
            into one file."""
            with local.cwd(project_src / "out"):
                extract_bc(project.name)
                cp(
                    local.path(project_src / "out" / project.name + ".bc"),
                    local.path(str(bb_cfg()["varats"]["result"].value)) /
                    project.name + ".bc"
                )

        def evaluate_analysis() -> None:
            """
            This step performs the actual analysis with the correct flags.
            Flags:
                -vara-CFR: to run a commit flow report
                -yaml-out-file=<path>: specify the path to store the results
            """
            project_src = local.path(bb_cfg()["varats"]["result"].value)

            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            outfile = "-yaml-out-file={}".format(
                bb_cfg()["varats"]["outfile"].value
            ) + "/" + str(project.name) + "-" + str(project.run_uuid) + ".yaml"
            run_cmd = opt["-vara-CD", "-vara-CFR", outfile,
                          project_src / project.name + ".bc"]
            run_cmd()

        analysis_actions = []
        if not os.path.exists(
            local.path(str(bb_cfg()["varats"]["result"].value)) / project.name +
            ".bc"
        ):
            analysis_actions.append(Prepare(self, evaluate_preparation))
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(self, evaluate_extraction))

        analysis_actions.append(Analyse(self, evaluate_analysis))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

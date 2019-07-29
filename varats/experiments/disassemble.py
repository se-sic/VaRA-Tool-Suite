"""
Module for disassembling bc files to llvm IR files.
This requires to run the compilation with WLLVM
"""
from pathlib import Path
from plumbum import local

import benchbuild.utils.actions as actions
from benchbuild.settings import CFG
from benchbuild.utils.cmd import mkdir, llvm_dis
from benchbuild.project import Project

from varats.experiments.extract import Extract

CFG["vara"] = {
    "outfile": {
        "default": "",
        "desc": "Path to store results of VaRA CFR analysis."
    },
    "result": {
        "default": "",
        "desc": "Path to store already annotated projects."
    },
}


class Disassemble(actions.Step):  # type: ignore
    """
    Step in an experiment to generate llvm intermediate representation out of
    bitcode previously generated in the experiment.
    """
    NAME = "DISASSEMBLE"
    DESCRIPTION = "Disassembles a bitcode file to intermediate representation."

    CACHE_DIR_TEMPLATE = "{cache_dir}/{project_name}/"
    LL_FILE_TEMPLATE = "{project_name}-{binary_name}-{project_version}.ll"

    def __init__(self, project: Project) -> None:
        super(Disassemble, self).__init__(
            obj=project, action_fn=self.disassemble)

    def disassemble(self) -> actions.StepResult:
        """
        This step extracts the intermediate representation of
        the bitcode of the project into one file.
        """
        if not self.obj:
            return
        project = self.obj

        cache_dir = self.CACHE_DIR_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))
        mkdir("-p", local.path() / cache_dir)

        for binary_name in project.BIN_NAMES:
            ll_file = cache_dir + self.LL_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            target_bc = cache_dir + Extract.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            if Path(target_bc).exists():
                llvm_dis(target_bc, '-o', ll_file)
            else:
                print("Could not find bitcode of binary '{name}' for " +
                      "disassembling.".format(name=binary_name))

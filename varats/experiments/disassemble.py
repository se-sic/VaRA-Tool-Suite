"""
Module for disassembling bc files to llvm IR files.
This requires to run the compilation with WLLVM
"""
from pathlib import Path
from plumbum import local
import subprocess

import benchbuild.utils.actions as actions
from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp, mkdir, llvm_dis
from benchbuild.utils.run import run
from benchbuild.project import Project

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
    NAME = "DISASSEMBLE"
    DESCRIPTION = "Disassembles an bitcode file to intermediate representation."

    LL_TARGET_FOLDER_TEMPLATE = "{project_builddir}/{project_src}/{project_name}"
    LL_FILE_TEMPLATE = "{binary_name}.ll"

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

        ll_target_folder = self.LL_TARGET_FOLDER_TEMPLATE.format(
            project_builddir=str(project.builddir),
            project_src=str(project.SRC_FILE),
            project_name=str(project.name))
        mkdir("-p", local.path() / ll_target_folder)

        target_bc_dir = local.path() / ll_target_folder

        for binary_name in project.BIN_NAMES:
            ll_file = local.path() / ll_target_folder /\
                self.LL_FILE_TEMPLATE.format(binary_name=str(binary_name))

            target_bc = target_bc_dir + '/.' + binary_name + '.o.bc'

            if Path(target_bc).exists():
                llvm_dis(target_bc, '-o', ll_file)
            else:
                print("Could not find bitcode of binary '{name}' for disassembling.".format(
                    name=binary_name))

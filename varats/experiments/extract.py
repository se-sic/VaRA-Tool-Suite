"""
Module for extracting bc files from generated binaries.
This requires to run the compilation with WLLVM
"""
from pathlib import Path
from plumbum import local

import benchbuild.utils.actions as actions
from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp, mkdir
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


class Extract(actions.Step):  # type: ignore
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    BC_CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"
    BC_FILE_TEMPLATE = "{project_name}-{binary_name}-{project_version}.bc"

    def __init__(self, project: Project) -> None:
        super(Extract, self).__init__(obj=project, action_fn=self.extract)

    def extract(self) -> actions.StepResult:
        """
        This step extracts the bitcode of the executable of the project
        into one file.
        """
        if not self.obj:
            return
        project = self.obj

        bc_cache_folder = self.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))
        mkdir("-p", local.path() / bc_cache_folder)

        for binary in project.binaries:
            bc_cache_file = bc_cache_folder + self.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary.name),
                project_version=str(project.version))

            target_binary = Path(project.builddir) / project.SRC_FILE /\
                binary

            extract_bc(target_binary)
            cp(str(target_binary) + ".bc", local.path() / bc_cache_file)

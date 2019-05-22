"""
Module for extracting bc files from generated binaries.
This requires to run the compilation with WLLVM
"""
from pathlib import Path
import attr
import benchbuild.utils.actions as actions

from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp, mkdir
from plumbum import local

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


@attr.s
class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    BC_CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"
    BC_FILE_TEMPLATE = "{project_name}-{binary_name}-{project_version}.bc"

    def __call__(self):
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

        for binary_name in project.BIN_NAMES:
            bc_cache_file = bc_cache_folder + self.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            target_binary = local.path(project.builddir) / project.SRC_FILE /\
                binary_name

            extract_bc(target_binary)

            if Path(target_binary).exists():
                cp(target_binary + ".bc", local.path() / bc_cache_file)
            else:
                print("Could not find binary '{name}' for extraction.".format(
                    name=binary_name))

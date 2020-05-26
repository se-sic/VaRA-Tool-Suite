"""
Module to provide WLLVM support for project compilation and extracting bc files
from generated binaries.

WLLVM is a compiler replacement/hook to compile projects with clang, producing
LLVM-IR files on the side. This allows us to hook into the build process and to
add additional passes/flags, without modifying build files, and later use the
generated bc files with LLVM.
"""

import typing as tp
from enum import Enum
from os import getenv
from pathlib import Path

import benchbuild.utils.actions as actions
from benchbuild.extensions import base
from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import extract_bc, cp, mkdir
from benchbuild.utils.compiler import cc
from benchbuild.utils.path import list_to_path, path_to_list
from plumbum import local

BC_FILE_TEMPLATE = "{project_name}-{binary_name}-{project_version}{" \
                   "bc_file_extensions}.bc"


class BCFileExtensions(Enum):
    DEBUG = 'dbg'
    NO_OPT = 'O0'
    OPT = 'O2'


class RunWLLVM(base.Extension):  # type: ignore
    """
    This extension implements the WLLVM compiler.

    This class is an extension that implements the WLLVM compiler with the
    required flags LLVM_COMPILER=clang and LLVM_OUTPUFILE=<path>. This compiler
    is used to transfer the complete project into LLVM-IR.
    """

    def __call__(self, compiler: cc, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        if str(compiler).endswith("clang++"):
            wllvm = local["wllvm++"]
        else:
            wllvm = local["wllvm"]

        env = BB_CFG["env"].value
        path = path_to_list(getenv("PATH", ""))
        path.extend(env.get("PATH", []))

        libs_path = path_to_list(getenv("LD_LIBRARY_PATH", ""))
        libs_path.extend(env.get("LD_LIBRARY_PATH", []))

        wllvm = wllvm.with_env(
            LLVM_COMPILER="clang",
            PATH=list_to_path(path),
            LD_LIBRARY_PATH=list_to_path(libs_path)
        )

        return self.call_next(wllvm, *args, **kwargs)


BB_CFG["varats"] = {
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
    """Extract step to extract a llvm bitcode file(.bc) from the project."""

    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    BC_CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"

    @staticmethod
    def get_bc_file_name(
        project_name: str, binary_name: str, project_version: str,
        bc_file_extensions: tp.List[BCFileExtensions]
    ):
        """Parses parameter information into a filename template to name a
        bitcode file."""

        if bc_file_extensions:
            project_bc_file_ext = '-'

            ext_sep = ""
            for ext in bc_file_extensions:
                project_bc_file_ext += (ext_sep + ext.value)
                ext_sep =  '_'
        else:
            project_bc_file_ext = ''

        return BC_FILE_TEMPLATE.format(
            project_name=project_name,
            binary_name=binary_name,
            project_version=project_version,
            bc_file_extensions=project_bc_file_ext
        )

    def __init__(
        self, project: Project, bc_file_extensions: tp.List[BCFileExtensions]
    ) -> None:
        super(Extract, self).__init__(obj=project, action_fn=self.extract)
        self.bc_file_extensions = bc_file_extensions

    def extract(self) -> actions.StepResult:
        """This step extracts the bitcode of the executable of the project into
        one file."""
        if not self.obj:
            return
        project = self.obj

        bc_cache_folder = self.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(BB_CFG["varats"]["result"]),
            project_name=str(project.name)
        )
        mkdir("-p", local.path() / bc_cache_folder)

        for binary in project.binaries:
            bc_cache_file = bc_cache_folder + self.get_bc_file_name(
                project_name=str(project.name),
                binary_name=str(binary.name),
                project_version=str(project.version),
                bc_file_extensions=self.bc_file_extensions
            )

            target_binary = Path(
                project.builddir
            ) / project.SRC_FILE / binary.path

            extract_bc(target_binary)
            cp(str(target_binary) + ".bc", local.path() / bc_cache_file)

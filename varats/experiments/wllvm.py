"""
Module to provide WLLVM support for project compilation and extracing bc files
from generated binaries.

WLLVM is a compiler replacement/hook to compile projects with clang, producing
LLVM-IR files on the side. This allows us to hook into the build process and to
add additional passes/flags, without modifying build files, and later use the
generated bc files with LLVM.
"""

import typing as tp
from os import getenv
from pathlib import Path

import benchbuild.utils.actions as actions
from benchbuild.extensions import base
from benchbuild.project import Project
from benchbuild.utils.cmd import cp, extract_bc, mkdir
from benchbuild.utils.compiler import cc
from benchbuild.utils.path import list_to_path, path_to_list
from plumbum import local

from varats.settings import get_benchbuild_config
from varats.utils.experiment_util import FunctionPEErrorWrapper, PEErrorHandler


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

        env = get_benchbuild_config()["env"].value
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


get_benchbuild_config()["varats"] = {
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
    BC_FILE_TEMPLATE = "{project_name}-{binary_name}-{project_version}.bc"

    def __init__(
        self,
        project: Project,
        handler: tp.Optional[PEErrorHandler] = None
    ) -> None:
        super().__init__(
            obj=project,
            action_fn=FunctionPEErrorWrapper(self.extract, handler)
            if handler else self.extract
        )

    def extract(self) -> actions.StepResult:
        """This step extracts the bitcode of the executable of the project into
        one file."""
        if not self.obj:
            return
        project = self.obj

        bc_cache_folder = self.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(get_benchbuild_config()["varats"]["result"]),
            project_name=str(project.name)
        )
        mkdir("-p", local.path() / bc_cache_folder)

        for binary in project.binaries:
            bc_cache_file = bc_cache_folder + self.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary.name),
                project_version=str(project.version)
            )

            target_binary = Path(
                project.builddir
            ) / project.SRC_FILE / binary.path

            extract_bc(target_binary)
            cp(str(target_binary) + ".bc", local.path() / bc_cache_file)

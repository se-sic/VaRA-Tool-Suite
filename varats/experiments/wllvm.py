"""
Module to provide WLLVM support for project compilation.

WLLVM is a comiler replacement/hook to compile projects with clang, producing
LLVM-IR files on the side. This allows us to hook into the build process and
to add additional passes/flags, without modifying build files, and later use
the generated bc files with LLVM.
"""

import typing as tp
from os import getenv

from plumbum import local

from benchbuild.extensions import base
from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.path import list_to_path, path_to_list


class RunWLLVM(base.Extension):  # type: ignore
    """
    This extension implements the WLLVM compiler.

    This class is an extension that implements the WLLVM compiler with the
    required flags LLVM_COMPILER=clang and LLVM_OUTPUFILE=<path>. This compiler
    is used to transfer the complete project into LLVM-IR.
    """

    def __call__(self, compiler: cc, *args: tp.Any,
                 **kwargs: tp.Any) -> tp.Any:
        if str(compiler).endswith("clang++"):
            wllvm = local["wllvm++"]
        else:
            wllvm = local["wllvm"]

        env = CFG["env"].value
        path = path_to_list(getenv("PATH", ""))
        path.extend(env.get("PATH", []))

        libs_path = path_to_list(getenv("LD_LIBRARY_PATH", ""))
        libs_path.extend(env.get("LD_LIBRARY_PATH", []))

        wllvm = wllvm.with_env(LLVM_COMPILER="clang",
                               PATH=list_to_path(path),
                               LD_LIBRARY_PATH=list_to_path(libs_path))

        return self.call_next(wllvm, *args, **kwargs)

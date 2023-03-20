"""
Module to provide WLLVM/GLLVM support for project compilation and extracting bc
files from generated binaries.

WLLVM/GLLVM is a compiler replacement/hook to compile projects with clang,
producing LLVM-IR files on the side. This allows us to hook into the build
process and to add additional passes/flags, without modifying build files, and
later use the generated bc files with LLVM.
"""

import shutil
import sys
import typing as tp
from enum import Enum
from os import getenv, path
from pathlib import Path

from benchbuild.extensions import base
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import cp, extract_bc, mkdir
from benchbuild.utils.compiler import cc
from benchbuild.utils.path import list_to_path, path_to_list
from plumbum import local

from varats.experiment.experiment_util import (
    FunctionPEErrorWrapper,
    PEErrorHandler,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.utils.settings import bb_cfg


class BCFileExtensions(Enum):
    """
    List of possible extensions that specify the way a BC file was created.

    An extension should be requested when a BC file needs to fulfill certain
    requirements, e.g., was compiled with debug metadata or compiled with
    optimizations.
    """
    value: str  # pylint: disable=invalid-name

    DEBUG = 'dbg'
    NO_OPT = 'O0'
    OPT = 'O2'
    TBAA = "TBAA"
    FEATURE = 'feature'
    BLAME = "blame"

    def __lt__(self, other: tp.Any) -> bool:
        if isinstance(other, BCFileExtensions):
            return self.value < other.value

        return False


class RunWLLVM(base.Extension):  # type: ignore
    """
    This extension implements the WLLVM/GLLVM compiler. GLLVM is used
    automatically if it is found in the PATH. Otherwise WLLVM is used.

    This class is an extension that implements the WLLVM/GLLVM compiler with the
    required flags LLVM_COMPILER=clang and LLVM_OUTPUFILE=<path>. This compiler
    is used to transfer the complete project into LLVM-IR.

    The distcc_hosts argument will instruct WLLVM/GLLVM to call distcc instead of
    clang directly. For possible values of distcc_hosts have a look at the
    "HOST SPECIFICATIONS" in the distcc man page.
    It is the user's responsibility to ensure that all distcc hosts are
    configured to use exactly the same compiler as localhost!

    Examples:

    * Usage without distcc:
      ``RunWLLVM()``
    * Usage with distcc enabled:
      ``RunWLLVM(distcc_hosts="localhost 192.168.1.1:3634/64")``
    """

    def __init__(
        self,
        *extensions: base.Extension,
        config: tp.Optional[tp.Dict[str, str]] = None,
        distcc_hosts: tp.Optional[str] = None,
        **kwargs: tp.Any
    ):
        super().__init__(*extensions, config=config, **kwargs)
        self._distcc_hosts = distcc_hosts

    def __create_distcc_scripts(self) -> tp.Tuple[Path, Path]:
        project_dir = Path(sys.argv[0]).parent
        distcc_cc = project_dir / "distcc-clang"
        distcc_cxx = project_dir / "distcc-clang++"

        if not distcc_cc.exists():
            distcc_cc.write_text("#!/usr/bin/env sh\ndistcc clang $@")
            # chmod +x
            distcc_cc.chmod(distcc_cc.stat().st_mode | 0o111)

        if not distcc_cxx.exists():
            distcc_cxx.write_text("#!/usr/bin/env sh\ndistcc clang++ $@")
            # chmod +x
            distcc_cxx.chmod(distcc_cc.stat().st_mode | 0o111)

        return distcc_cc, distcc_cxx

    def __call__(self, compiler: cc, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        if is_gllvm_available():
            compiler_wrapper = "gclang"
        else:
            compiler_wrapper = "wllvm"

        if str(compiler).endswith("clang++"):
            compiler_wrapper += "++"

        wllvm = local[compiler_wrapper]

        env = bb_cfg()["env"].value
        env_path_list = path_to_list(getenv("PATH", ""))
        env_path_list = env.get("PATH", []) + env_path_list

        libs_path = path_to_list(getenv("LD_LIBRARY_PATH", ""))
        libs_path = env.get("LD_LIBRARY_PATH", []) + libs_path

        wllvm = wllvm.with_env(
            LLVM_COMPILER="clang",
            PATH=list_to_path(env_path_list),
            LD_LIBRARY_PATH=list_to_path(libs_path)
        )

        if self._distcc_hosts:
            distcc_cc, distcc_cxx = self.__create_distcc_scripts()
            wllvm.env["DISTCC_HOSTS"] = self._distcc_hosts
            wllvm.env["LLVM_CC_NAME"] = distcc_cc
            wllvm.env["LLVM_CXX_NAME"] = distcc_cxx

        return self.call_next(wllvm, *args, **kwargs)


class Extract(actions.ProjectStep):  # type: ignore
    """Extract step to extract a llvm bitcode file(.bc) from the project."""

    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    BC_CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"

    project: VProject

    @staticmethod
    def get_bc_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None
    ) -> str:
        """Parses parameter information into a filename template to name a
        bitcode file."""

        if bc_file_extensions is None:
            bc_file_extensions = []

        if bc_file_extensions:
            experiment_bc_file_ext = '-'

            ext_sep = ""
            for ext in sorted(bc_file_extensions):
                experiment_bc_file_ext += (ext_sep + ext.value)
                ext_sep = '_'
        else:
            experiment_bc_file_ext = ''

        return f"{project_name}-{binary_name}-{project_version}" \
               f"{experiment_bc_file_ext}.bc"

    def __init__(
        self,
        project: Project,
        bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None,
        handler: tp.Optional[PEErrorHandler] = None
    ) -> None:
        super().__init__(project=project)
        self.__action_fn = tp.cast(
            tp.Callable[..., tp.Any],
            FunctionPEErrorWrapper(self.extract, handler)
            if handler else self.extract
        )

        if bc_file_extensions is None:
            bc_file_extensions = []

        self.bc_file_extensions = bc_file_extensions

    def __call__(self) -> actions.StepResult:
        return tp.cast(actions.StepResult, self.__action_fn())

    def extract(self) -> actions.StepResult:
        """This step extracts the bitcode of the executable of the project into
        one file."""
        self.project: VProject

        bc_cache_folder = self.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(bb_cfg()["varats"]["result"]),
            project_name=str(self.project.name)
        )
        mkdir("-p", local.path() / bc_cache_folder)

        for binary in self.project.binaries:
            bc_cache_file = bc_cache_folder + self.get_bc_file_name(
                project_name=str(self.project.name),
                binary_name=str(binary.name),
                project_version=self.project.version_of_primary,
                bc_file_extensions=self.bc_file_extensions
            )

            target_binary = Path(self.project.source_of_primary) / binary.path
            if is_gllvm_available():
                from benchbuild.utils.cmd import get_bc
                get_bc(target_binary)
            else:
                extract_bc(target_binary)
            cp(str(target_binary) + ".bc", local.path() / bc_cache_file)

        return actions.StepResult.OK


def project_bc_files_in_cache(
    project: Project,
    required_bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]]
) -> bool:
    """
    Checks if all bc files, corresponding to the projects binaries, are in the
    cache.

    Args:
        project: the project
        required_bc_file_extensions: list of required file extensions

    Returns: True, if all BC files are present, False otherwise.
    """

    all_files_present = True
    for binary in project.binaries:
        all_files_present &= path.exists(
            local.path(
                Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                    cache_dir=str(bb_cfg()["varats"]["result"]),
                    project_name=str(project.name)
                ) + Extract.get_bc_file_name(
                    project_name=str(project.name),
                    binary_name=binary.name,
                    project_version=project.version_of_primary,
                    bc_file_extensions=required_bc_file_extensions
                )
            )
        )

    return all_files_present


def _create_default_bc_file_creation_actions(
    project: Project, required_bc_file_extensions: tp.List[BCFileExtensions],
    extraction_error_handler: tp.Optional[PEErrorHandler]
) -> tp.List[actions.Step]:
    """
    Creates the default action pipeline to compile a project and run the BC
    files extraction step.

    Args:
        project: the project to compile
        required_bc_file_extensions: list of required file extensions
        extraction_error_handler: error handler to report errors during
                                  the extraction step

    Returns: default compile and extract action steps
    """
    analysis_actions = []
    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        Extract(
            project,
            required_bc_file_extensions,
            handler=extraction_error_handler
        )
    )
    return analysis_actions


def get_bc_cache_actions(
    project: Project,
    bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None,
    extraction_error_handler: tp.Optional[PEErrorHandler] = None,
    bc_action_creator: tp.Callable[
        [Project, tp.List[BCFileExtensions], tp.Optional[PEErrorHandler]],
        tp.List[actions.Step]] = _create_default_bc_file_creation_actions
) -> tp.List[actions.Step]:
    """
    Builds the action pipeline, if needed, to fill the BC file cache that
    provides BC files for the compiled binaries of a project.

    Args:
        project: the project to compile
        bc_file_extensions: list of bc file extensions
        extraction_error_handler: error handler to report errors during
                                  the extraction step
        bc_action_creator: alternative BC cache actions creation callback

    Returns: required actions to populate the BC cache
    """

    if not project_bc_files_in_cache(project, bc_file_extensions):
        return bc_action_creator(
            project, bc_file_extensions if bc_file_extensions else [],
            extraction_error_handler
        )

    return []


def get_cached_bc_file_path(
    project: Project,
    binary: ProjectBinaryWrapper,
    required_bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None,
) -> Path:
    """
    Look up the path to a BC file from the BC cache.

    Args:
        project: the project
        binary: which corresponds to the BC file
        required_bc_file_extensions: list of required file extensions

    Returns: path to the cached BC file
    """
    bc_cache_folder = local.path(
        Extract.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(bb_cfg()["varats"]["result"]),
            project_name=str(project.name)
        )
    )

    bc_file_path = bc_cache_folder / Extract.get_bc_file_name(
        project_name=project.name,
        binary_name=binary.name,
        project_version=project.version_of_primary,
        bc_file_extensions=required_bc_file_extensions
    )
    if not bc_file_path.exists():
        raise LookupError(
            "No corresponding BC file found in cache. Project was probably not"
            " compiled with the correct compile/extract action."
        )
    return Path(bc_file_path)


def is_gllvm_available() -> bool:
    return None not in {
        shutil.which(binary) for binary in ["gclang", "gclang++", "get-bc"]
    }

"""
Implements the base blame experiment.
"""

import typing as tp
from os import path

from plumbum import local

from benchbuild.project import Project
from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
import benchbuild.utils.actions as actions

from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM
from varats.utils.experiment_util import (FunctionPEErrorWrapper,
                                          PEErrorHandler)


def setup_basic_blame_experiment(experiment: Experiment, project: Project,
                                 result_folder: str,
                                 compile_error_file: str) -> None:
    """
    Setup the project for a blame experiment.
        - run time extensions
        - compile time extensions
        - prepare compiler
        - configure C/CXX flags
    """
    # Add the required runtime extensions to the project(s).
    project.runtime_extension = run.RuntimeExtension(project, experiment) \
        << time.RunWithTime()

    # Add the required compiler extensions to the project(s).
    project.compiler_extension = compiler.RunCompiler(project, experiment) \
        << RunWLLVM() \
        << run.WithTimeout()

    # Add own error handler to compile step.
    project.compile = FunctionPEErrorWrapper(
        project.compile, PEErrorHandler(result_folder, compile_error_file))

    # This c-flag is provided by VaRA and it suggests to use the git-blame
    # annotation.
    project.cflags = ["-fvara-GB"]


def generate_basic_blame_experiment_actions(project: Project
                                            ) -> tp.List[actions.Step]:
    """
    Generate the basic actions for a blame experiment.
        - handle caching of BC files
        - compile project, if needed
    """
    analysis_actions = []

    # Check if all binaries have corresponding BC files
    all_files_present = True
    for binary_name in project.BIN_NAMES:
        all_files_present &= path.exists(
            local.path(
                Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                    cache_dir=str(CFG["vara"]["result"]),
                    project_name=str(project.name)) +
                Extract.BC_FILE_TEMPLATE.format(project_name=str(project.name),
                                                binary_name=binary_name,
                                                project_version=str(
                                                    project.version))))

    if not all_files_present:
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(Extract(project))

    return analysis_actions

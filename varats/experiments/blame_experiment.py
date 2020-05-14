"""Implements the base blame experiment, making it easier to create different
blame experiments that have a similar experiment setup."""

import typing as tp
from os import path

import benchbuild.utils.actions as actions
from benchbuild.experiment import Experiment
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from plumbum import local

from varats.data.report import BaseReport
from varats.experiments.wllvm import RunWLLVM, Extract, BCFileExtensions
from varats.utils.experiment_util import get_default_compile_error_wrapped


def setup_basic_blame_experiment(
    experiment: Experiment, project: Project, report_type: tp.Type[BaseReport],
    result_folder_template: str
) -> None:
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
    project.compile = get_default_compile_error_wrapped(
        project, report_type, result_folder_template
    )

    # This c-flag is provided by VaRA and it suggests to use the git-blame
    # annotation.
    project.cflags = ["-fvara-GB"]


def generate_basic_blame_experiment_actions(
    project: Project, bc_file_extensions: tp.List[BCFileExtensions]
) -> tp.List[actions.Step]:
    """
    Generate the basic actions for a blame experiment.

    - handle caching of BC files
    - compile project, if needed
    """
    analysis_actions = []

    # Check if all binaries have corresponding BC files
    all_files_present = True

    for binary in project.binaries:
        all_files_present &= path.exists(
            local.path(
                Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                    cache_dir=str(BB_CFG["varats"]["result"]),
                    project_name=str(project.name)
                ) + Extract.get_bc_file_name(
                    project_name=str(project.name),
                    binary_name=binary.name,
                    project_version=str(project.version),
                    bc_file_extensions=bc_file_extensions
                )
            )
        )

    if not all_files_present:
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(Extract(project, bc_file_extensions))

    return analysis_actions

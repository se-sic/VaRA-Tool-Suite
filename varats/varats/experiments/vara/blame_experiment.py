"""Implements the base blame experiment, making it easier to create different
blame experiments that have a similar experiment setup."""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    PEErrorHandler,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
)
from varats.report.report import BaseReport


def setup_basic_blame_experiment(
    experiment: VersionExperiment, project: Project,
    report_type: tp.Type[BaseReport]
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
        experiment.get_handle(), project, report_type
    )

    # This c-flag is provided by VaRA and it suggests to use the git-blame
    # annotation.
    project.cflags += ["-fvara-GB"]


def generate_basic_blame_experiment_actions(
    project: Project,
    bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None,
    extraction_error_handler: tp.Optional[PEErrorHandler] = None
) -> tp.List[actions.Step]:
    """
    Generate the basic actions for a blame experiment.

    - handle caching of BC files
    - compile project, if needed

    Args:
        project: reference to the BB project
        bc_file_extensions: list of bitcode file extensions (e.g. opt, no opt)
        extraction_error_handler: handler to manage errors during the
                                  extraction process
    """
    return get_bc_cache_actions(
        project, bc_file_extensions, extraction_error_handler
    )

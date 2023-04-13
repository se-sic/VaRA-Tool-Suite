"""Implements the base feature blame experiment, making it easier to create different
feature-blame experiments that have a similar experiment setup."""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import clang
import os
from benchbuild.utils import actions

from varats.data.reports.feature_blame_report import FeatureBlameReport as FBR
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    get_default_compile_error_wrapped,
    wrap_unlimit_stack_size,
    create_default_analysis_failure_handler,
    PEErrorHandler,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
)
from varats.report.report import BaseReport


def setup_basic_feature_blame_experiment(
    experiment: VersionExperiment, project: Project,
    report_type: tp.Type[BaseReport]
) -> None:
    """
    Setup the project for a feature blame experiment.

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
    project.cflags += ["-fvara-GB", "-fvara-feature"]

    for binary in project.binaries:
            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.

            current_dir = os.getcwd()
            file = current_dir + "/tmp/" + project.name + "/" + "main"

            clang_params = [
                "-fvara-GB", "-fvara-feature", "-S", "-emit-llvm", file + ".cpp" ,"-c", "-o", file + ".bc"
            ]

            clang_cmd = clang[clang_params]

            clang_cmd = wrap_unlimit_stack_size(clang_cmd)

            exec_func_with_pe_error_handler(
                clang_cmd,
                create_default_analysis_failure_handler(
                    experiment.get_handle(), project, FBR
                )
            )


def generate_basic_feature_blame_experiment_actions(
    project: Project,
    bc_file_extensions: tp.Optional[tp.List[BCFileExtensions]] = None,
    extraction_error_handler: tp.Optional[PEErrorHandler] = None
) -> tp.List[actions.Step]:
    """
    Generate the basic actions for a feature blame experiment.

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

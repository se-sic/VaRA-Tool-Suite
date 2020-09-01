"""
Execute showcase cpp examples with Phasar's tracing of environment variables.

This class implements the environment tracing data flow analysis of Phasar. We
run the analysis on exemplary cpp files. The cpp examples can be found in the
https://github.com/se-passau/vara-perf-tests repository. The results of each
analysis get written into a PhasarReport, which lists, what examples produced a
valid json result and which ones failed.
"""

import typing as tp
from os import path

import benchbuild.utils.actions as actions
from benchbuild import Experiment, Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir, phasar, timeout
from plumbum import local

from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.env_trace_report import EnvTraceReport as ENVR
from varats.experiments.wllvm import Extract, RunWLLVM
from varats.utils.experiment_util import (
    FunctionPEErrorWrapper,
    PEErrorHandler,
    wrap_unlimit_stack_size,
    exec_func_with_pe_error_handler,
)
from varats.utils.settings import bb_cfg


class PhasarEnvIFDS(actions.Step):  # type: ignore
    """Analyse a project with Phasar's IFDS that traces environment variables
    inside a project."""

    NAME = "PhasarEnvIFDS"
    DESCRIPTION = "Calls the environment tracing analysis of phasar and "\
        + "stores the results in a json file."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -D: tells which data flow analysis to run
            IFDS_EnvironmentVariableTracing: the data flow analysis we need
            -m: takes an input LLVM IR file
            -O: designate a named output file
        """

        if not self.obj:
            return
        project = self.obj
        # Set up cache directory for bitcode files.
        bc_cache_dir = Extract.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(bb_cfg()["varats"]["result"]),
            project_name=str(project.name)
        )

        # Define the output directory.
        result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", result_folder)

        timeout_duration = '8h'

        for binary in project.binaries:
            # Combine the input bitcode file's name
            bc_target_file = Extract.get_bc_file_name(
                project_name=str(project.name),
                binary_name=str(binary.name),
                project_version=project.version_of_primary
            )

            # Define result file.
            result_file = ENVR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            # Define output file name of failed runs
            error_file = ENVR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Failed,
                file_ext=".txt"
            )

            # Put together the run command
            phasar_run_cmd = phasar[
                "-D", "IFDS_EnvironmentVariableTracing", "-m",
                "{cache_folder}/{bc_file}".
                format(cache_folder=bc_cache_dir, bc_file=bc_target_file), "-O",
                "{res_folder}/{res_file}".
                format(res_folder=result_folder, res_file=result_file)]

            phasar_run_cmd = wrap_unlimit_stack_size(phasar_run_cmd)

            # Run the phasar command with custom error handler and timeout
            exec_func_with_pe_error_handler(
                timeout[timeout_duration, phasar_run_cmd],
                PEErrorHandler(result_folder, error_file, timeout_duration)
            )


class PhasarEnvironmentTracing(Experiment):  # type: ignore
    """Generates a inter-procedural data flow analysis (IFDS) on a project's
    binaries and traces environment variables."""

    NAME = "PhasarEnvironmentTracing"

    REPORT_TYPE = ENVR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s)
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s)
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step
        project.compile = FunctionPEErrorWrapper(
            project.compile,
            PEErrorHandler(
                PhasarEnvIFDS.RESULT_FOLDER_TEMPLATE.format(
                    result_dir=str(bb_cfg()["varats"]["outfile"]),
                    project_dir=str(project.name)
                ),
                ENVR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=project.version_of_primary,
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError
                )
            )
        )

        analysis_actions = []

        # Not run all steps if cached results exist
        all_cache_files_present = True
        for binary in project.binaries:
            all_cache_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(bb_cfg()["varats"]["result"]),
                        project_name=str(project.name)
                    ) + Extract.get_bc_file_name(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=project.version_of_primary
                    )
                )
            )

            if not all_cache_files_present:
                analysis_actions.append(actions.Compile(project))
                analysis_actions.append(Extract(project))
                break

        analysis_actions.append(PhasarEnvIFDS(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

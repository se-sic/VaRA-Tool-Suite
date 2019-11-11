"""
Execute showcase cpp examples with Phasar's tracing of environment variables.
This class implements the environment tracing data flow analysis of Phasar.
We run the analysis on exemplary cpp files. The cpp examples can be
found in the https://github.com/se-passau/vara-perf-tests repository.
The results of each analysis get written into a PhasarReport, which lists, what
examples produced a valid json result and which ones failed.
"""

import typing as tp
from os import path
import resource

from plumbum import local

from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.project import Project
from benchbuild.experiment import Experiment
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import phasar, mkdir, timeout
from varats.data.reports.env_trace_report import EnvTraceReport as ENVR
from varats.data.report import FileStatusExtension as FSE
from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler, FunctionPEErrorWrapper,
    PEErrorHandler)


class PhasarEnvIFDS(actions.Step):  # type: ignore
    """
    Analyse a project with Phasar's IFDS that traces environment variables
    inside a project.
    """

    NAME = "PhasarEnvIFDS"
    DESCRIPTION = "Calls the environment tracing analysis of phasar and "\
        + "stores the results in a json file."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project):
        super(PhasarEnvIFDS, self).__init__(
            obj=project, action_fn=self.analyze)

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
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))

        # Define the output directory.
        result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(CFG["vara"]["outfile"]),
            project_dir=str(project.name))

        mkdir("-p", result_folder)

        timeout_duration = '8h'

        for binary in project.binaries:
            # Combine the input bitcode file's name
            bc_target_file = Extract.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary.name),
                project_version=str(project.version))

            # Define result file.
            result_file = ENVR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            # Define output file name of failed runs
            error_file = ENVR.get_file_name(project_name=str(project.name),
                                            binary_name=binary.name,
                                            project_version=str(
                                                project.version),
                                            project_uuid=str(project.run_uuid),
                                            extension_type=FSE.Failed,
                                            file_ext=".txt")

            # Put together the run command
            phasar_run_cmd = phasar["-D", "IFDS_EnvironmentVariableTracing",
                                    "-m", "{cache_folder}/{bc_file}"
                                    .format(cache_folder=bc_cache_dir,
                                            bc_file=bc_target_file),
                                    "-O", "{res_folder}/{res_file}".format(
                                        res_folder=result_folder,
                                        res_file=result_file)]

            # Run the phasar command with custom error handler and timeout
            exec_func_with_pe_error_handler(
                timeout[timeout_duration, phasar_run_cmd],
                PEErrorHandler(result_folder, error_file,
                               phasar_run_cmd, timeout_duration))


class UnlimitStackSize(actions.Step):  # type: ignore
    """
    Set higher user limits on stack size for RAM intense experiments.
    Basically the same as calling the shell built-in ulimit.
    """

    NAME = "Unlimit stack size"
    DESCRIPTION = "Sets new resource limits."

    def __init__(self, project: Project):
        super(UnlimitStackSize, self).__init__(
            obj=project, action_fn=self.__call__)

    def __call__(self) -> actions.StepResult:
        """
        Same as 'ulimit -s 16777216' in a shell.
        """
        resource.setrlimit(resource.RLIMIT_STACK, (16777216, 16777216))


class PhasarEnvironmentTracing(Experiment):  # type: ignore
    """
    Generates a inter-procedural data flow analysis (IFDS) on a project's
    binaries and traces environment variables.
    """

    NAME = "PhasarEnvironmentTracing"

    REPORT_TYPE = ENVR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in
        the call in a fixed order.
        """

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
                    result_dir=str(CFG["vara"]["outfile"]),
                    project_dir=str(project.name)),
                ENVR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=str(project.version),
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError)))

        analysis_actions = []

        # Not run all steps if cached results exist
        all_cache_files_present = True
        for binary in project.binaries:
            all_cache_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(CFG["vara"]["result"]),
                        project_name=str(project.name)) +
                    Extract.BC_FILE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=str(project.version))))

            if not all_cache_files_present:
                analysis_actions.append(actions.Compile(project))
                analysis_actions.append(Extract(project))
                break

        analysis_actions.append(UnlimitStackSize(project))
        analysis_actions.append(PhasarEnvIFDS(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

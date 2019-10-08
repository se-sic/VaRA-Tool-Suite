import typing as tp
from os import path

from plumbum import local

from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.project import Project
from benchbuild.experiment import Experiment
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import phasar, mkdir, timeout
from varats.data.reports.phasar_report import PhasarReport as PHR
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
    DESCRIPTION = "Calls the environment tracing analysis of phasar and stores"
    + " the results in a json file."

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

        for binary_name in project.BIN_NAMES:

            # Combine the input bitcode file's name.
            bc_target_file = Extract.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            # Define result file.
            result_file = PHR.get_file_name(
                project_name=str(project.name),
                binary_name=binary_name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            # Define output file name of failed runs.
            error_file = PHR.get_file_name(
                project_name=str(project.name),
                binary_name=binary_name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Failed,
                file_ext=".txt")

            # Put together the run command
            phasar_run_cmd = phasar["-D", "IFDS_EnvironmentVariableTracing",
                                    "{cache_folder}/{bc_file}"
                                    .format(cache_folder=bc_cache_dir,
                                            bc_file=bc_target_file),
                                    "-O", "{res_folder}/{res_file}".format(
                                        res_folder=result_folder,
                                        res_file=result_file)]

            # Run the phasar command with custom error handler and timeout.
            exec_func_with_pe_error_handler(
                timeout[timeout_duration, phasar_run_cmd],
                PEErrorHandler(result_folder, error_file,
                               phasar_run_cmd, timeout_duration))


class PhasarEnvironmentTracing(Experiment):
    """
    Generates a inter-procedural data flow analysis (IDFS) on a project's
    binaries and traces environment variables.
    """

    NAME = "PhasarEnvironmentTracing"

    REPORT_TYPE = PHR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in
        the call in a fixed order.
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = FunctionPEErrorWrapper(
            project.compile,
            PEErrorHandler(
                PhasarEnvIFDS.RESULT_FOLDER_TEMPLATE.format(
                    result_dir=str(CFG["vara"]["outfile"]),
                    project_dir=str(project.name)),
                PHR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=str(project.version),
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError)))

        project.cflags = []
        analysis_actions = []

        # Not run all steps if cached results exist.
        all_cache_files_present = True
        for binary_name in project.BIN_NAMES:
            all_cache_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(CFG["vara"]["result"]),
                        project_name=str(project.name)) +
                    Extract.BC_FILE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version))))

            if not all_cache_files_present:
                analysis_actions.append(actions.Compile(project))
                analysis_actions.append(Extract(project))
                break

        analysis_actions.append(PhasarEnvIFDS(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

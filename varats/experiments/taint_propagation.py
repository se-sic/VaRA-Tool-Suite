"""
Execute showcase cpp examples with VaRA and Phasar to compare their taint
analyses.

This class implements the full commit taint flow analysis (MTFA) graph
generation of the variability-aware region analyzer (VaRA) and Phasar.
We run the analyses on exemplary cpp files. Then we compare the results of both
analyses to the expected results via LLVM FileCheck.
Both the cpp examples and the filecheck files validating the results can be
found in the https://github.com/se-passau/vara-perf-tests repository.
The results of each filecheck get written into a special TaintPropagation-
Report, which lists, what examples produced the correct result and which ones
failed.
"""

import typing as tp
from os import path

from plumbum import local

from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.project import Project
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import opt, cp, mkdir, timeout, FileCheck
from varats.data.reports.taint_report import TaintPropagationReport as TPR
from varats.data.report import FileStatusExtension as FSE
from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler, FunctionPEErrorWrapper,
    VaRAVersionExperiment, PEErrorHandler)


class VaraMTFACheck(actions.Step):
    """
    Analyse a project with VaRA and generate the output of the taint analysis.
    """

    NAME = "VaraMTFACheck"
    DESCRIPTION = "Generate a full MTFA on the exemplary taint test files and"\
        + " compare them against the expected result."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    MTFA_OUTPUT_DIR = "{project_builddir}/{project_src}/{project_name}"
    MTFA_RESULT_FILE = "{binary_name}.mtfa"

    FILE_CHECK_EXPECTED = "{project_name}-{binary_name}-{project_version}.txt"

    def __init__(self, project: Project):
        super(VaraMTFACheck, self).__init__(
            obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -vara-CD:         activate VaRA's commit detection
            -print-Full-MTFA: to run a taint flow analysis
        """

        if not self.obj:
            return
        project = self.obj

        # Set up cache directory for bitcode files
        bc_cache_dir = Extract.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))

        # Define the output directory
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(CFG["vara"]["outfile"]),
            project_dir=str(project.name))
        mkdir("-p", vara_result_folder)

        # Set up temporary work directory for the experiment
        perf_dir = self.MTFA_OUTPUT_DIR.format(
            project_builddir=str(project.builddir),
            project_src=str(project.SRC_FILE),
            project_name=str(project.NAME))
        mkdir("-p", perf_dir)

        timeout_duration = '8h'

        for binary_name in project.BIN_NAMES:

            # Combine the input bitcode file's name
            bc_target_file = Extract.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            # Put together the path to the bc file and the opt command of vara
            vara_run_cmd = opt["-vara-CD", "-print-Full-MTFA",
                               "{cache_folder}/{bc_file}"
                               .format(cache_folder=bc_cache_dir,
                                       bc_file=bc_target_file),
                               "-o", "/dev/null"]

            file_check_expected = self.FILE_CHECK_EXPECTED.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            file_check_cmd = FileCheck["{fc_dir}{fc_exp_file}".format(
                fc_dir=bc_cache_dir, fc_exp_file=file_check_expected)]

            # Define output report file
            result_file = TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary_name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            # Run the MTFA command with custom error handler and timeout
            # TODO currently produces empty yaml file if successful
            exec_func_with_pe_error_handler(
                timeout[timeout_duration, vara_run_cmd] | file_check_cmd
                > "{res_folder}/{res_file}".format(
                    res_folder=vara_result_folder, res_file=result_file),
                PEErrorHandler(vara_result_folder,
                               TPR.get_file_name(
                                   project_name=str(project.name),
                                   binary_name=binary_name,
                                   project_version=str(project.version),
                                   project_uuid=str(project.run_uuid),
                                   extension_type=FSE.Failed),
                               vara_run_cmd,
                               timeout_duration))


class FileCheckExpected(actions.Step):  # type: ignore
    """
    Store the expected filecheck results of a project in the bc cache directory
    and rename the txt files to a unique name matching the run.
    """

    NAME = "EXPECT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"
    FC_CACHE_TEMPLATE = "{project_name}-{binary_name}-{project_version}.txt"

    FC_FILE_SOURCE_DIR = "{project_builddir}/{project_src}/{project_name}"
    EXPECTED_FC_FILE = "{binary_name}.txt"

    def __init__(self, project: Project) -> None:
        super(FileCheckExpected, self).__init__(obj=project,
                                                action_fn=self.store_expected)

    def store_expected(self) -> actions.StepResult:
        """
        This step caches the txt files with the expected filecheck results
        for the project.
        """
        if not self.obj:
            return
        project = self.obj

        cache_folder = self.CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))
        mkdir("-p", local.path() / cache_folder)

        for binary_name in project.BIN_NAMES:
            fc_cache_file = cache_folder + self.FC_CACHE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            target_dir = self.FC_FILE_SOURCE_DIR.format(
                project_builddir=str(project.builddir),
                project_src=str(project.SRC_FILE),
                project_name=str(project.name))

            target_file = self.EXPECTED_FC_FILE.format(binary_name=binary_name)

            target = "{dir}/{file}".format(dir=target_dir, file=target_file)

            if path.exists(target):
                cp(target, local.path() / fc_cache_file)
            else:
                print("Could not find expected filecheck " +
                      "'{name}.txt' for caching.".format(name=binary_name))
                # raise?


class TaintPropagation(VaRAVersionExperiment):
    """
    Generates a taint flow analysis (MTFA) of the project(s) specified in the
    call.
    """

    NAME = "TaintPropagation"

    REPORT_TYPE = TPR

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

        # Add own error handler to compile step
        project.compile = FunctionPEErrorWrapper(
            project.compile,
            PEErrorHandler(
                VaraMTFACheck.RESULT_FOLDER_TEMPLATE.format(
                    result_dir=str(CFG["vara"]["outfile"]),
                    project_dir=str(project.name)),
                TPR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=str(project.version),
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError)))

        project.cflags = ["-fvara-handleRM=Commit"]

        analysis_actions = []

        # Not run all steps if cached results exist
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

            all_cache_files_present &= path.exists(
                local.path(
                    FileCheckExpected.CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(CFG["vara"]["result"]),
                        project_name=str(project.name)) +
                    FileCheckExpected.FC_CACHE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version))))

            if not all_cache_files_present:
                break

        if not all_cache_files_present:
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))
            analysis_actions.append(FileCheckExpected(project))

        analysis_actions.append(VaraMTFACheck(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

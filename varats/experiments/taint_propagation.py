"""
Execute showcase cpp examples with vara to analyse taints.

This class implements the full commit taint flow analysis (MTFA) graph
generation of the variability-aware region analyzer (VaRA).
"""

import typing as tp
from os import path

from plumbum import local

from benchbuild.extensions import compiler, run, time
from benchbuild.settings import CFG
from benchbuild.project import Project
import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import opt, mkdir, timeout

from varats.data.reports.taint_report import TaintPropagationReport as TPR
from varats.data.report import FileStatusExtension as FSE
from varats.experiments.extract import Extract
from varats.experiments.wllvm import RunWLLVM
from varats.utils.experiment_util import (
    exec_func_with_pe_error_handler, FunctionPEErrorWrapper,
    VaRAVersionExperiment, PEErrorHandler)


class MTFAGeneration(actions.Step):
    """
    Analyse a project with VaRA and generate the output of the taint analysis.
    """

    NAME = "MTFAGeneration"
    DESCRIPTION = "Analyses the bitcode with MTFA of VaRA."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project):
        super(MTFAGeneration, self).__init__(obj=project,
                                                  action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -print-Full-MTFA: to run a taint flow analysis
        """

        if not self.obj:
            return
        project = self.obj

        # change output to tmp dir, where the cpp files are from
        tmp_project_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(CFG["vara"]["outfile"]),
            project_dir=str(project.name))

        bc_cache_dir = Extract.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))

        mkdir("-p", tmp_project_folder)

        for binary_name in project.BIN_NAMES:

            bc_target_file = Extract.BC_FILE_TEMPLATE.format(
                project_name=str(project.name),
                binary_name=str(binary_name),
                project_version=str(project.version))

            result_file = TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary_name,
                project_version=str(project.version),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success)

            run_cmd = opt["-vara-CD", "-print-Full-MTFA",
                          "{cache_folder}/{bc_file}"
                          .format(cache_folder=bc_cache_dir,
                       bc_file=bc_target_file),
                          "-o", "/dev/null"]

            timeout_duration = '8h'

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd]
                > "{res_folder}/{res_file}".format(
                    res_folder=tmp_project_folder,
                    res_file=result_file),
                PEErrorHandler(
                    tmp_project_folder,
                    TPR.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version),
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed),
                    run_cmd, timeout_duration))

                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version),
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed), run_cmd, timeout_duration))


class TaintPropagation(VaRAVersionExperiment):
    """
    Generates a taint flow analysis (MTFA) of the project(s) specified in the
    call.
    """

    NAME = "TaintPropagation"

    REPORT_TYPE = TPR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in
        the call in a fixed order."""

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
                MTFAGeneration.RESULT_FOLDER_TEMPLATE.format(
                    result_dir=str(CFG["vara"]["outfile"]),
                    project_dir=str(project.name)),
                TPR.get_file_name(
                    project_name=str(project.name),
                    binary_name="all",
                    project_version=str(project.version),
                    project_uuid=str(project.run_uuid),
                    extension_type=FSE.CompileError),
            ))

        project.cflags = ["-fvara-handleRM=Commit"]

        analysis_actions = []

        # Not run all steps if cached results exist
        all_bc_files_present = True
        for binary_name in project.BIN_NAMES:
            all_bc_files_present &= path.exists(
                local.path(
                    Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                        cache_dir=str(CFG["vara"]["result"]),
                        project_name=str(project.name)) +
                    Extract.BC_FILE_TEMPLATE.format(
                        project_name=str(project.name),
                        binary_name=binary_name,
                        project_version=str(project.version))))

        if not all_bc_files_present:
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project))

        analysis_actions.append(MTFAGeneration(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

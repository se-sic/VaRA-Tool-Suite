"""
Execute showcase cpp examples with VaRA to compare the taint analysis to other
statically analysis frameworks.

This class implements the full commit taint flow analysis (MTFA) graph
generation of the variability-aware region analyzer (VaRA). We run the analyses
on exemplary cpp files. The cpp examples can be found in the
https://github.com/se-passau/vara-perf-tests repository. The output LLVM IR
files with annotated meta data are written into the result files for each
executed binary.
"""

import typing as tp

import benchbuild.utils.actions as actions
from benchbuild import Project  # type: ignore
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir, opt, timeout

from varats.data.reports.taint_report import TaintPropagationReport as TPR
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    PEErrorHandler,
    get_default_compile_error_wrapped,
    create_default_compiler_error_handler,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.report.report import FileStatusExtension as FSE
from varats.utils.settings import bb_cfg


class VaraMTFACheck(actions.Step):  # type: ignore
    """Analyse a project with VaRA and generate the output of the taint flow
    analysis."""

    NAME = "VaraMTFACheck"
    DESCRIPTION = "Generate a full MTFA on the exemplary taint test files."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.analyze)

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

        # Define the output directory.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )
        mkdir("-p", vara_result_folder)

        timeout_duration = '8h'

        for binary in project.binaries:
            # Combine the input bitcode file's name
            bc_target_file = get_cached_bc_file_path(project, binary)

            # Define empty success file.
            result_file = TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success,
                file_ext=".ll"
            )

            # Define output file name of failed runs
            error_file = TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Failed,
                file_ext=TPR.FILE_TYPE
            )

            # Put together the path to the bc file and the opt command of vara
            vara_run_cmd = opt["-vara-CD", "-print-Full-MTFA",
                               str(bc_target_file), "-o", "/dev/null"]

            # Run the MTFA command with custom error handler and timeout
            exec_func_with_pe_error_handler(
                timeout[timeout_duration,
                        vara_run_cmd] > "{res_folder}/{res_file}".
                format(res_folder=vara_result_folder, res_file=result_file),
                PEErrorHandler(
                    vara_result_folder, error_file, timeout_duration
                )
            )


class VaRATaintPropagation(VersionExperiment):
    """Generates a taint flow analysis (MTFA) of the project(s) specified in the
    call."""

    NAME = "VaRATaintPropagation"
    REPORT_TYPE = TPR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            project, self.REPORT_TYPE, VaraMTFACheck.RESULT_FOLDER_TEMPLATE
        )

        project.cflags = ["-fvara-handleRM=Commit"]

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            extraction_error_handler=create_default_compiler_error_handler(
                project, self.REPORT_TYPE
            )
        )

        analysis_actions.append(VaraMTFACheck(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

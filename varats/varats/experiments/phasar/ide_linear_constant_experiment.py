"""Module for phasar LinearConstantAnalysis analyses."""
import typing as tp
from os import path

import benchbuild.utils.actions as actions
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir
from plumbum import local

from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.empty_report import EmptyReport
from varats.experiments.wllvm import Extract, RunWLLVM
from varats.utils.experiment_util import (
    PEErrorHandler,
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_default_compile_error_wrapped,
    exec_func_with_pe_error_handler,
)
from varats.utils.settings import bb_cfg


class IDELinearConstantAnalysis(actions.Step):  # type: ignore
    """Analysis step to run phasar's IDELinearConstantAnalysis on a project."""

    NAME = "IDELinearConstantAnalysis"
    DESCRIPTION = (
        "Flow- and context-sensitive analysis that tracks constant "
        "variables and variables that linearly depend on constant "
        "values through the program."
    )

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self,
        project: Project,
    ):
        super().__init__(obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """Run phasar's IDELinearConstantAnalysis analysis."""
        if not self.obj:
            return
        project = self.obj

        bc_cache_folder = local.path(
            Extract.BC_CACHE_FOLDER_TEMPLATE.format(
                cache_dir=str(bb_cfg()["varats"]["result"]),
                project_name=str(project.name)
            )
        )
        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        varats_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", varats_result_folder)

        phasar = local["phasar-llvm"]
        for binary in project.binaries:
            bc_file = bc_cache_folder / Extract.get_bc_file_name(
                project_name=project.name,
                binary_name=binary.name,
                project_version=project.version_of_primary
            )

            result_file = EmptyReport.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            phasar_params = ["-m", bc_file, "-C", "CHA", "-D", "ide-lca"]

            run_cmd = wrap_unlimit_stack_size(phasar[phasar_params])

            run_cmd = (run_cmd > f'{varats_result_folder}/{result_file}')

            exec_func_with_pe_error_handler(
                run_cmd,
                PEErrorHandler(
                    varats_result_folder,
                    EmptyReport.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=project.version_of_primary,
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed,
                        file_ext=".txt"
                    )
                )
            )


class IDELinearConstantAnalysisExperiment(VersionExperiment):
    """Experiment class to build and analyse a project with an
    IDELinearConstantAnalysis."""

    NAME = "PhasarIDELinearConstantAnalysis"

    REPORT_TYPE = EmptyReport

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            project, EmptyReport,
            IDELinearConstantAnalysis.RESULT_FOLDER_TEMPLATE
        )

        varats_result_folder = \
            f"{bb_cfg()['varats']['outfile']}/{project.name}"

        error_handler = PEErrorHandler(
            varats_result_folder,
            EmptyReport.get_file_name(
                project_name=str(project.name),
                binary_name="all",
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.CompileError,
                file_ext=".txt"
            )
        )

        analysis_actions = []

        # Check if all binaries have corresponding BC files
        all_files_present = True
        for binary in project.binaries:
            all_files_present &= path.exists(
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
        if not all_files_present:
            analysis_actions.append(actions.Compile(project))
            analysis_actions.append(Extract(project, handler=error_handler))

        analysis_actions.append(IDELinearConstantAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

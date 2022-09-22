""""""
import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import iteridebenchmark, time

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    wrap_unlimit_stack_size,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    get_varats_result_folder,
    exec_func_with_pe_error_handler,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class IterIDEBasicStats(actions.Step):  # type: ignore

    NAME = "EmptyAnalysis"
    DESCRIPTION = "Analyses nothing."

    obj: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle

    def analyze(self) -> None:
        for binary in self.obj.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, EmptyReport, self.obj, binary
            )

            phasar_params = [
                "--old", "-D", "lca", "-m",
                get_cached_bc_file_path(
                    self.obj, binary,
                    [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
                )
            ]

            phasar_cmd = iteridebenchmark[phasar_params]

            run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.obj,
                    self.__experiment_handle.report_spec().main_report
                )
            )


class IDELinearConstantAnalysisExperiment(
    VersionExperiment, shorthand="IterIDE"
):
    """Experiment class to build and analyse a project with an
    IterIDEBasicStats."""

    NAME = "PhasarIterIDE"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, EmptyReport
        )

        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
        ]

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            bc_file_extensions=bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(IterIDEBasicStats(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

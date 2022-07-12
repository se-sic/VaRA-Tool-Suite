"""Implements the global analysis comparision experiment to determine the effect
of running an analysis with globals support."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import phasar_globals
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    get_varats_result_folder,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    get_default_compile_error_wrapped,
    create_new_success_result_filename,
)
from varats.experiment.wllvm import (
    get_cached_bc_file_path,
    BCFileExtensions,
    get_bc_cache_actions,
    RunWLLVM,
)
from varats.report.report import ReportSpecification


class RunGlobalsTestAnalysis(actions.Step):  # type: ignore
    """Analyse a project with and without phasars global support."""

    NAME = "GlobalsReportGeneration"
    DESCRIPTION = "Run phasar LCA with and without globals support"

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        globals_active: bool
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle
        self.__globals_active = globals_active

    def analyze(self) -> actions.StepResult:
        """This step performs the actual comparision, running the analysis with
        and without phasars global support."""
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            if self.__globals_active:
                report_type: tp.Union[
                    tp.Type[GlobalsReportWith],
                    tp.Type[GlobalsReportWithout]] = GlobalsReportWith
            else:
                report_type = GlobalsReportWithout

            result_file = create_new_success_result_filename(
                self.__experiment_handle, report_type, project, binary
            )

            phasar_params = [
                f"--auto-globals={'ON' if self.__globals_active else 'OFF'}",
                "-m",
                get_cached_bc_file_path(
                    project, binary,
                    [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
                ), "-o", f"{vara_result_folder}/{result_file}"
            ]

            run_cmd = phasar_globals[phasar_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, report_type,
                    Path(vara_result_folder)
                )
            )

        return actions.StepResult.OK


class GlobalsComparision(VersionExperiment, shorthand="GAC"):
    """Compare the effect size of a phasar analysis with globals or without."""

    NAME = "GlobalsComparision"

    REPORT_SPEC = ReportSpecification(GlobalsReportWith, GlobalsReportWithout)
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
        ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = get_bc_cache_actions(
            project, bc_file_extensions,
            create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        for _ in range(0, 10):
            analysis_actions.append(
                RunGlobalsTestAnalysis(project, self.get_handle(), True)
            )
            analysis_actions.append(
                RunGlobalsTestAnalysis(project, self.get_handle(), False)
            )

        # Clean up the generated files afterwards
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

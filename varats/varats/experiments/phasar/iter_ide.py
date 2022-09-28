""""""
import os
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import iteridebenchmark, phasar_llvm, time
from plumbum import RETCODE

from varats.data.reports.phasar_iter_ide import PhasarIterIDEStatsReport
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
    ZippedExperimentSteps,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class AnalysisType(Enum):

    value: str

    TYPE_STATE = "typestate"
    TAINT = "taint"
    LCA = "lca"

    @staticmethod
    def convert_from(value: str) -> tp.List['AnalysisType']:
        enabled_analysis_types = []
        for analysis_type in AnalysisType:
            if analysis_type.value in value:
                enabled_analysis_types.append(analysis_type)

        return enabled_analysis_types

    def __str__(self) -> str:
        return f"{self.value}"


def _get_enabled_analyses() -> tp.List[AnalysisType]:
    """Allows overriding of analyses run by an experiment, this should only be
    used for testing purposes, as the experiment will not generate all the
    required results."""
    env_analysis_selection = os.getenv("PHASAR_ANALYSIS")
    if env_analysis_selection:
        return AnalysisType.convert_from(env_analysis_selection)

    return [at for at in AnalysisType]


class IterIDETimeOld(actions.ProjectStep):  # type: ignore

    NAME = "OldIDESolver"
    DESCRIPTION = "Analyses old IDESolver"

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper,
        analysis_type: AnalysisType
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary
        self.__analysis_type = analysis_type

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        phasar_params = [
            "--old", "-D",
            str(self.__analysis_type), "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = iteridebenchmark[phasar_params]

        result_file = tmp_dir / f"old_{self.__analysis_type}_{self.__num}.txt"
        run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (old)")

        return actions.StepResult.OK


class IterIDETimeNew(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolver"
    DESCRIPTION = "Analyses new IDESolver"

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper,
        analysis_type: AnalysisType
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary
        self.__analysis_type = analysis_type

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        phasar_params = [
            "-D",
            str(self.__analysis_type), "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = iteridebenchmark[phasar_params]

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"
        run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (new)")

        return actions.StepResult.OK


class PhasarIDEStats(actions.ProjectStep):  # type: ignore

    NAME = "EmptyAnalysis"
    DESCRIPTION = "Analyses nothing."

    project: VProject

    def __init__(self, project: Project, binary: ProjectBinaryWrapper):
        super().__init__(project=project)
        self.__binary = binary

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.compute_stats(tmp_dir)

    def compute_stats(self, tmp_dir: Path) -> None:
        if self.__binary.type.is_library:
            extra_lib_params = ["--entry-points", "__ALL__"]
        else:
            extra_lib_params = []

        phasar_params = [
            "-S", *extra_lib_params, "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = phasar_llvm[phasar_params]

        result_file = tmp_dir / "phasar_bc_stats.txt"
        run_cmd = phasar_cmd > str(result_file)

        run_cmd()

        return actions.StepResult.OK


# TODO: fix wrong name
class IDELinearConstantAnalysisExperiment(
    VersionExperiment, shorthand="IterIDE"
):
    """Experiment class to build and analyse a project with an
    IterIDEBasicStats."""

    NAME = "PhasarIterIDE"

    REPORT_SPEC = ReportSpecification(PhasarIterIDEStatsReport)

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
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
        ]

        # Only consider the main/first binary
        binary = project.binaries[0]
        result_file = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project, binary
        )

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            bc_file_extensions=bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file, [
                    PhasarIDEStats(project, binary), *[
                        IterIDETimeOld(project, 0, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                    ], *[
                        IterIDETimeNew(project, 0, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                    ]
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

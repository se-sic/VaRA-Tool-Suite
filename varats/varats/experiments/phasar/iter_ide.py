""""""
import os
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild import Project
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import (
    iteridebenchmark,
    phasar_llvm,
    time,
    mkdir,
    touch,
)
from benchbuild.utils.requirements import Requirement, SlurmMem
from plumbum import RETCODE

from varats.data.reports.phasar_iter_ide import PhasarIterIDEStatsReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_default_compile_error_wrapped,
    create_default_compiler_error_handler,
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


class WorklistKind(Enum):

    value: str

    STACK = "stack"
    QUEUE = "queue"
    DEPTH_PRIORITY_QUEUE = "depth-prio"
    DEPTH_PRIORITY_QUEUE_REVERSED = "depth-prio-rev"
    SIZE_PRIORITY_QUEUE = "size-prio"
    SIZE_PRIORITY_QUEUE_REVERSED = "size-prio-rev"

    @staticmethod
    def convert_from(value: str) -> tp.List['WorklistKind']:
        enabled_wl_kinds = []
        for wl_kind in WorklistKind:
            if wl_kind.value in value:
                enabled_wl_kinds.append(wl_kind)

        return enabled_wl_kinds

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


def _get_enabled_worklist_kinds() -> tp.List[WorklistKind]:
    """Allows overriding of analyses run by an experiment, this should only be
    used for testing purposes, as the experiment will not generate all the
    required results."""
    env_wl_selection = os.getenv("PHASAR_WORKLIST")
    if env_wl_selection:
        return WorklistKind.convert_from(env_wl_selection)

    return [wl for wl in WorklistKind]


class IterIDETimeOld(actions.ProjectStep):  # type: ignore

    NAME = "OldIDESolver"
    DESCRIPTION = "Analyse old IDESolver"

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
        tmp_dir /= f"old_{self.__analysis_type}"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "--old", "-D",
            str(self.__analysis_type), "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"old_{self.__analysis_type}_{self.__num}.txt"
        run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (old)")
            return actions.StepResult.OK

        if ret_code != 0:
            error_file = tmp_dir / f"old_{self.__analysis_type}_{self.__num}_err_{ret_code}.txt"
            touch(error_file)
            return actions.StepResult.ERROR

        return actions.StepResult.OK


class IterIDETimeNew(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolver"
    DESCRIPTION = "Analyse new IDESolver"

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper,
        analysis_type: AnalysisType, worklist_kind: WorklistKind
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary
        self.__analysis_type = analysis_type
        self.__worklist_kind = worklist_kind

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        tmp_dir /= f"new_{self.__analysis_type}_{self.__worklist_kind}"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--worklist",
            str(self.__worklist_kind), "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"
        run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (new)")
            return actions.StepResult.OK

        if ret_code != 0:
            error_file = tmp_dir / f"old_{self.__analysis_type}_{self.__num}_err_{ret_code}.txt"
            touch(error_file)
            return actions.StepResult.ERROR

        return actions.StepResult.OK


class IterIDETimeNewJF1(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverJF1"
    DESCRIPTION = "Analyse new IDESolver with alternative jump functions representation"

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
        tmp_dir /= f"new_{self.__analysis_type}_jf1"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--jf1", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"
        run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (new)")
            return actions.StepResult.OK

        if ret_code != 0:
            error_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}_err_{ret_code}.txt"
            touch(error_file)
            return actions.StepResult.ERROR

        return actions.StepResult.OK


class IterIDECompareAnalysisResults(actions.ProjectStep):  # type: ignore

    NAME = "CmpIDESolverResults"
    DESCRIPTION = "Analyse IDESolver results for equivalence"

    project: VProject

    def __init__(
        self, project: Project, binary: ProjectBinaryWrapper,
        analysis_type: AnalysisType
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__analysis_type = analysis_type

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--compare-results-to-old", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"cmp_{self.__analysis_type}.txt"

        (ret_code, stdout, stderr) = phasar_cmd.run(retcode=None)

        with open(result_file, "w") as output_file:
            output_file.write(f"Error Code: {ret_code}\n")
            output_file.write("\nStdout:\n")
            output_file.write(stdout)
            output_file.write("\nStderr:\n")
            output_file.write(stderr)

        if ret_code == 137:
            print("Found OOM (cmp)")
            return actions.StepResult.OK

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

    def compute_stats(self, tmp_dir: Path) -> actions.StepResult:
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
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]
    CONTAINER = ContainerImage().run("apt", "install", "-y", "time")

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
        print(f"{project.name}")
        if len(project.binaries) < 1:
            return []
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

        reps = range(0, 1)

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file, [
                    PhasarIDEStats(project, binary), *[
                        IterIDECompareAnalysisResults(
                            project, binary, analysis_type
                        ) for analysis_type in _get_enabled_analyses()
                    ], *[
                        IterIDETimeOld(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ], *[
                        IterIDETimeNew(
                            project, rep, binary, analysis_type, worklist_kind
                        ) for analysis_type in _get_enabled_analyses()
                        for worklist_kind in _get_enabled_worklist_kinds()
                        for rep in reps
                    ], *[
                        IterIDETimeNewJF1(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ]
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

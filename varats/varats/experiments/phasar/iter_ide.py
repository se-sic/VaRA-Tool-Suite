""""""
import os
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild import Project
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.extensions import compiler, run
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import Step
from benchbuild.utils.cmd import (
    iteridebenchmark,
    phasar_llvm,
    time,
    timeout,
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
    if (env_analysis_selection := os.getenv("PHASAR_ANALYSIS")):
        return AnalysisType.convert_from(env_analysis_selection)

    return [at for at in AnalysisType]


def _get_enabled_worklist_kinds() -> tp.List[WorklistKind]:
    """Allows overriding of analyses run by an experiment, this should only be
    used for testing purposes, as the experiment will not generate all the
    required results."""
    if (env_wl_selection := os.getenv("PHASAR_WORKLIST")):
        return WorklistKind.convert_from(env_wl_selection)

    return [wl for wl in WorklistKind]


def _run_phasar_analysis(phasar_cmd, result_file) -> actions.StepResult:
    run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]
    run_cmd = timeout['-v', '5h', run_cmd]

    (ret_code, stdout, stderr) = run_cmd.run(retcode=None)

    if ret_code != 0:
        if ret_code == 137:
            error_file = result_file.with_suffix(".oom")
            touch(error_file)
            return actions.StepResult.OK

        if "timeout: " in stderr:
            error_file = result_file.with_suffix(".timeout")
            touch(error_file)
            return actions.StepResult.OK

        error_file = result_file.with_suffix(".err")
        with open(error_file, "w") as output_file:
            output_file.write(f"Error Code: {ret_code}\n")
            output_file.write("\nStdout:\n")
            output_file.write(stdout)
            output_file.write("\nStderr:\n")
            output_file.write(stderr)

        return actions.StepResult.ERROR

    return actions.StepResult.OK


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

        return _run_phasar_analysis(phasar_cmd, result_file)

        # run_cmd = time['-v', '-o', f'{result_file}', phasar_cmd]
        # run_cmd = timeout['5h', run_cmd]

        # (ret_code, stdout, stderr) = run_cmd.run(retcode=None)

        # if ret_code == 137:
        #     print("Found OOM (old)")
        #     return actions.StepResult.OK

        # if ret_code != 0:
        #     error_file = tmp_dir / f"old_{self.__analysis_type}_{self.__num}_err_{ret_code}.txt"
        #     with open(error_file, "w") as output_file:
        #         output_file.write(f"Error Code: {ret_code}\n")
        #         output_file.write("\nStdout:\n")
        #         output_file.write(stdout)
        #         output_file.write("\nStderr:\n")
        #         output_file.write(stderr)

        #     return actions.StepResult.ERROR

        # return actions.StepResult.OK


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

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewRec(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverRec"
    DESCRIPTION = "Analyse new IDESolver recursive"

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
        tmp_dir /= f"new_{self.__analysis_type}_rec"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--recursive", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_rec_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


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

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewJF1Rec(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverJF1Rec"
    DESCRIPTION = "Analyse new IDESolver with alternative jump functions representation in recursive mode"

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
        tmp_dir /= f"new_{self.__analysis_type}_jf1_rec"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--jf1", "--recursive", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_rec_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewJF3(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverJF3"
    DESCRIPTION = "Analyse new IDESolver with JF2 jump functions representation + EndSummaryTab"

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
        tmp_dir /= f"new_{self.__analysis_type}_jf3"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--enable-endsummary-tab", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewJF3Rec(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverJF3Rec"
    DESCRIPTION = "Analyse new IDESolver with JF2 jump functions representation + EndSummaryTab + recursive"

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
        tmp_dir /= f"new_{self.__analysis_type}_jf3_rec"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--enable-endsummary-tab", "--recursive",
            "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_rec_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewGC(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverGC"
    DESCRIPTION = "Analyse new IDESolver with enabled jump-functions garbage collection"

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
        tmp_dir /= f"new_{self.__analysis_type}_gc"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--GC=enable", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


class IterIDETimeNewGCJF1(actions.ProjectStep):  # type: ignore

    NAME = "NewIDESolverGCJF1"
    DESCRIPTION = "Analyse new IDESolver with enabled jump-functions garbage collection and JF1 table"

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
        tmp_dir /= f"new_{self.__analysis_type}_gc_jf1"
        mkdir("-p", tmp_dir)

        phasar_params = [
            "-D",
            str(self.__analysis_type), "--GC=enable", "--jf1", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd = wrap_unlimit_stack_size(iteridebenchmark[phasar_params])

        result_file = tmp_dir / f"new_{self.__analysis_type}_{self.__num}.txt"

        return _run_phasar_analysis(phasar_cmd, result_file)


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


class IterIDESolverStats(actions.ProjectStep):  # type: ignore

    NAME = "IterIDESolverStats"
    DESCRIPTION = "Statistics of the IterIDE Solver for the analysis run"

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

        phasar_params_jf2 = [
            "-D",
            str(self.__analysis_type), "-S", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_params_jf1 = [
            "-D",
            str(self.__analysis_type), "-S", "--jf1", "-m",
            get_cached_bc_file_path(
                self.project, self.__binary,
                [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
            )
        ]

        phasar_cmd_jf2 = wrap_unlimit_stack_size(
            iteridebenchmark[phasar_params_jf2]
        )
        phasar_cmd_jf1 = wrap_unlimit_stack_size(
            iteridebenchmark[phasar_params_jf1]
        )

        result_file_jf2 = tmp_dir / f"stats_{self.__analysis_type}_jf2.txt"
        result_file_jf1 = tmp_dir / f"stats_{self.__analysis_type}_jf1.txt"

        (ret_code, stdout, stderr) = phasar_cmd_jf2.run(retcode=None)

        with open(result_file_jf2, "w") as output_file:
            output_file.write(f"Error Code: {ret_code}\n")
            output_file.write("\nStdout:\n")
            output_file.write(stdout)
            output_file.write("\nStderr:\n")
            output_file.write(stderr)

        if ret_code == 137:
            print("Found OOM (stats JF2)")

        (ret_code, stdout, stderr) = phasar_cmd_jf1.run(retcode=None)

        with open(result_file_jf1, "w") as output_file:
            output_file.write(f"Error Code: {ret_code}\n")
            output_file.write("\nStdout:\n")
            output_file.write(stdout)
            output_file.write("\nStderr:\n")
            output_file.write(stderr)

        if ret_code == 137:
            print("Found OOM (stats JF1)")

        return actions.StepResult.OK


# class IterIDESolverStatsDbg(actions.ProjectStep):  # type: ignore

#     NAME = "IterIDESolverStatsDbg"
#     DESCRIPTION = "Statistics of the IterIDE Solver for the analysis run"

#     project: VProject

#     def __init__(
#         self, project: Project, binary: ProjectBinaryWrapper,
#         analysis_type: AnalysisType
#     ):
#         super().__init__(project=project)
#         self.__binary = binary
#         self.__analysis_type = analysis_type

#     def __call__(self, tmp_dir: Path) -> actions.StepResult:
#         return self.analyze(tmp_dir)

#     def analyze(self, tmp_dir: Path) -> actions.StepResult:
#         mkdir("-p", tmp_dir)

#         phasar_params_jf2 = [
#             "-D",
#             str(self.__analysis_type), "-S", "--log", "-m",
#             get_cached_bc_file_path(
#                 self.project, self.__binary,
#                 [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
#             )
#         ]

#         phasar_params_jf1 = [
#             "-D",
#             str(self.__analysis_type), "-S", "--log", "--jf1", "-m",
#             get_cached_bc_file_path(
#                 self.project, self.__binary,
#                 [BCFileExtensions.NO_OPT, BCFileExtensions.TBAA]
#             )
#         ]

#         phasar_cmd_jf2 = wrap_unlimit_stack_size(
#             iteridebenchmark[phasar_params_jf2]
#         )
#         phasar_cmd_jf1 = wrap_unlimit_stack_size(
#             iteridebenchmark[phasar_params_jf1]
#         )

#         result_file_jf2 = tmp_dir / f"stats_{self.__analysis_type}_jf2.txt"
#         result_file_jf1 = tmp_dir / f"stats_{self.__analysis_type}_jf1.txt"

#         (ret_code, stdout, stderr) = phasar_cmd_jf2.run(retcode=None)

#         with open(result_file_jf2, "w") as output_file:
#             output_file.write(f"Error Code: {ret_code}\n")
#             output_file.write("\nStdout:\n")
#             output_file.write(stdout)
#             output_file.write("\nStderr:\n")
#             output_file.write(stderr)

#         if ret_code == 137:
#             print("Found OOM (stats JF2)")

#         (ret_code, stdout, stderr) = phasar_cmd_jf1.run(retcode=None)

#         with open(result_file_jf1, "w") as output_file:
#             output_file.write(f"Error Code: {ret_code}\n")
#             output_file.write("\nStdout:\n")
#             output_file.write(stdout)
#             output_file.write("\nStderr:\n")
#             output_file.write(stderr)

#         if ret_code == 137:
#             print("Found OOM (stats JF1)")

#         return actions.StepResult.OK


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


class PhasarBCStatsExperiment(VersionExperiment, shorthand="BCStats"):
    """Experiment class to collect some statistics about the LLVM IR of the
    target projects within the paper config."""

    NAME = "PhasarBCStats"
    REPORT_SPEC = ReportSpecification(PhasarIterIDEStatsReport)

    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
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

        reps = range(0, 3)

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file, [
                    PhasarIDEStats(project, binary),
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


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

        reps = range(0, 3)

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file,
                [
                    PhasarIDEStats(project, binary),
                    *[
                        IterIDECompareAnalysisResults(
                            project, binary, analysis_type
                        ) for analysis_type in _get_enabled_analyses()
                    ],
                    *[
                        IterIDESolverStats(project, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                    ],
                    *[
                        IterIDETimeOld(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNew(
                            project, rep, binary, analysis_type,
                            WorklistKind.STACK
                        )
                        for analysis_type in _get_enabled_analyses()
                        # for worklist_kind in _get_enabled_worklist_kinds()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewJF1(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewJF3(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewGC(project, rep, binary, analysis_type)
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewGCJF1(
                            project, rep, binary, analysis_type
                        )
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewRec(
                            project, rep, binary, analysis_type,
                            WorklistKind.STACK
                        )
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewJF1Rec(
                            project, rep, binary, analysis_type
                        )
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                    *[
                        IterIDETimeNewJF3Rec(
                            project, rep, binary, analysis_type
                        )
                        for analysis_type in _get_enabled_analyses()
                        for rep in reps
                    ],
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


# class IDELinearConstantAnalysisExperimentDebug(
#     VersionExperiment, shorthand="IterIDEDebug"
# ):
#     """Experiment class to build and analyse a project with an
#     IterIDEBasicStats."""

#     NAME = "PhasarIterIDEDebug"

#     REPORT_SPEC = ReportSpecification(PhasarIterIDEStatsReport)
#     REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]
#     CONTAINER = ContainerImage().run("apt", "install", "-y", "time")

#     def actions_for_project(
#         self, project: Project
#     ) -> tp.MutableSequence[actions.Step]:
#         """
#         Returns the specified steps to run the project(s) specified in the call
#         in a fixed order.

#         Args:
#             project: to analyze
#         """

#         # Add the required runtime extensions to the project(s).
#         project.runtime_extension = run.RuntimeExtension(project, self)

#         # Add the required compiler extensions to the project(s).
#         project.compiler_extension = compiler.RunCompiler(project, self) \
#             << RunWLLVM()

#         # Add own error handler to compile step.
#         project.compile = get_default_compile_error_wrapped(
#             self.get_handle(), project, self.REPORT_SPEC.main_report
#         )

#         project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
#         bc_file_extensions = [
#             BCFileExtensions.NO_OPT,
#             BCFileExtensions.TBAA,
#         ]

#         # Only consider the main/first binary
#         print(f"{project.name}")
#         if len(project.binaries) < 1:
#             return []
#         binary = project.binaries[0]
#         result_file = create_new_success_result_filepath(
#             self.get_handle(), self.REPORT_SPEC.main_report, project, binary
#         )

#         analysis_actions = []

#         analysis_actions += get_bc_cache_actions(
#             project,
#             bc_file_extensions=bc_file_extensions,
#             extraction_error_handler=create_default_compiler_error_handler(
#                 self.get_handle(), project, self.REPORT_SPEC.main_report
#             )
#         )

#         reps = range(0, 3)

#         analysis_actions.append(
#             ZippedExperimentSteps(
#                 result_file, [
#                     *[
#                         IterIDESolverStatsDbg(project, binary, analysis_type)
#                         for analysis_type in _get_enabled_analyses()
#                     ]
#                 ]
#             )
#         )
#         analysis_actions.append(actions.Clean(project))

#         return analysis_actions

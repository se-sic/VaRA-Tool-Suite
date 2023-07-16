"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import shutil
import tempfile
import textwrap
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import (
    ProjectStep,
    Step,
    StepResult,
    Compile,
    Clean,
)
from benchbuild.utils.cmd import time
from plumbum import local, ProcessExecutionError

from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReportAggregate,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    WithUnlimitedStackSize,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_current_config_id,
    get_default_compile_error_wrapped,
    get_extra_config_options,
    ZippedExperimentSteps,
)
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    RunVaRATracedXRayWorkloads,
    FeatureInstrType,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import (
    PatchProvider,
    ApplyPatch,
    RevertPatch,
)
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import ReportSpecification, ReportTy, BaseReport
from varats.report.tef_report import TEFReport, TEFReportAggregate
from varats.utils.git_util import ShortCommitHash


class AnalysisProjectStepBase(ProjectStep):

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "json",
        reps=2
    ):
        super().__init__(project=project)
        self._binary = binary
        self._report_file_ending = report_file_ending
        self._result_pre_fix = result_post_fix
        self._reps = reps


class MultiPatchReport(
    BaseReport, tp.Generic[ReportTy], shorthand="MPR", file_type=".zip"
):

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)
        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            # TODO: clean up
            for report in Path(tmp_result_dir).iterdir():
                if report.name.startswith("old"):
                    self.__old = report_type(report)
                elif report.name.startswith("new"):
                    self.__new = report_type(report)

            if not self.__old or not self.__new:
                raise AssertionError(
                    "Reports where missing in the file {report_path=}"
                )

    def get_old_report(self) -> ReportTy:
        return self.__old

    def get_new_report(self) -> ReportTy:
        return self.__new


class MPRTRA(
    MultiPatchReport[TimeReportAggregate], shorthand="MPRTRA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReportAggregate)


class MPRTEFA(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRTEFA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReportAggregate)


class MPRPIMA(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRPIMA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfInfluenceTraceReportAggregate)


class ReCompile(ProjectStep):
    NAME = "RECOMPILE"
    DESCRIPTION = "Recompile the project"

    def __call__(self, _: tp.Any) -> StepResult:
        try:
            self.project.recompile()

        except ProcessExecutionError:
            self.status = StepResult.ERROR
        self.status = StepResult.OK

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Recompile", indent * " "
        )


class RunGenTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "json",
        reps=2
    ):
        super().__init__(
            project, binary, result_post_fix, report_file_ending, reps
        )

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / f"{self._result_pre_fix}_rep_measures"
            with ZippedReportFolder(zip_tmp_dir) as reps_tmp_dir:
                for rep in range(0, self._reps):
                    for prj_command in workload_commands(
                        self.project, self._binary, [WorkloadCategory.EXAMPLE]
                    ):
                        local_tracefile_path = Path(reps_tmp_dir) / (
                            f"trace_{prj_command.command.label}_{rep}"
                            f".{self._report_file_ending}"
                        )
                        with local.env(VARA_TRACE_FILE=local_tracefile_path):
                            pb_cmd = prj_command.command.as_plumbum(
                                project=self.project
                            )
                            print(
                                f"Running example {prj_command.command.label}"
                            )

                            extra_options = get_extra_config_options(
                                self.project
                            )
                            with cleanup(prj_command):
                                pb_cmd(
                                    *extra_options,
                                    retcode=self._binary.valid_exit_codes
                                )

        return StepResult.OK


def setup_actions_for_vara_experiment(
    experiment: FeatureExperiment, project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBase]
) -> tp.MutableSequence[actions.Step]:

    project.cflags += experiment.get_vara_feature_cflags(project)

    threshold = 0 if project.DOMAIN.value is ProjectDomains.TEST else 100
    project.cflags += experiment.get_vara_tracing_cflags(
        instr_type, project=project, instruction_threshold=threshold
    )

    project.ldflags += experiment.get_vara_tracing_ldflags()

    # Add the required runtime extensions to the project(s).
    project.runtime_extension = bb_ext.run.RuntimeExtension(
        project, experiment
    ) << bb_ext.time.RunWithTime()

    # Add the required compiler extensions to the project(s).
    project.compiler_extension = bb_ext.compiler.RunCompiler(
        project, experiment
    ) << WithUnlimitedStackSize()

    # Add own error handler to compile step.
    project.compile = get_default_compile_error_wrapped(
        experiment.get_handle(), project, experiment.REPORT_SPEC.main_report
    )

    binary = project.binaries[0]
    if binary.type != BinaryType.EXECUTABLE:
        raise AssertionError("Experiment only works with executables.")

    result_filepath = create_new_success_result_filepath(
        experiment.get_handle(),
        experiment.get_handle().report_spec().main_report, project, binary,
        get_current_config_id(project)
    )

    patch_provider = PatchProvider.get_provider_for_project(project)
    patches = patch_provider.get_patches_for_revision(
        ShortCommitHash(project.version_of_primary)
    )
    print(f"{patches=}")

    patch_steps = []
    for patch in patches:
        print(f"Got patch with path: {patch.path}")
        patch_steps.append(ApplyPatch(project, patch))
        patch_steps.append(ReCompile(project))
        patch_steps.append(
            analysis_step(
                project, binary, result_post_fix=f"patched_{patch.shortname}"
            )
        )
        patch_steps.append(RevertPatch(project, patch))

    # TODO: integrate patches
    analysis_actions = []

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath,
            [analysis_step(project, binary, result_post_fix="old")] +
            patch_steps
        )
    )
    analysis_actions.append(actions.Clean(project))

    return analysis_actions


class TEFProfileRunner(FeatureExperiment, shorthand="TEFp"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfiler"

    REPORT_SPEC = ReportSpecification(MPRTEFA)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self, project, FeatureInstrType.TEF, RunGenTracedWorkloads
        )


class PIMProfileRunner(FeatureExperiment, shorthand="PIMp"):
    """Test runner for feature performance."""

    NAME = "RunPIMProfiler"

    REPORT_SPEC = ReportSpecification(MPRPIMA)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self, project, FeatureInstrType.PERF_INFLUENCE_TRACE,
            RunGenTracedWorkloads
        )


class RunBackBoxBaseline(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "txt",
        reps=2
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__result_pre_fix = result_post_fix
        self.__reps = reps

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / f"{self.__result_pre_fix}_rep_measures"
            with ZippedReportFolder(zip_tmp_dir) as reps_tmp_dir:
                for rep in range(0, self.__reps):
                    for prj_command in workload_commands(
                        self.project, self.__binary, [WorkloadCategory.EXAMPLE]
                    ):
                        time_report_file = Path(reps_tmp_dir) / (
                            f"baseline_{prj_command.command.label}_{rep}"
                            f".{self.__report_file_ending}"
                        )

                        pb_cmd = prj_command.command.as_plumbum(
                            project=self.project
                        )
                        print(f"Running example {prj_command.command.label}")

                        timed_pb_cmd = time["-v", "-o", time_report_file,
                                            pb_cmd]

                        extra_options = get_extra_config_options(self.project)
                        with cleanup(prj_command):
                            timed_pb_cmd(
                                *extra_options,
                                retcode=self.__binary.valid_exit_codes
                            )

        return StepResult.OK


class BlackBoxBaselineRunner(FeatureExperiment, shorthand="BBBase"):
    """Test runner for feature performance."""

    NAME = "GenBBBaseline"

    REPORT_SPEC = ReportSpecification(MPRTRA)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-flto", "-fuse-ld=lld", "-fno-omit-frame-pointer"]

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        binary = project.binaries[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        patch_provider = PatchProvider.get_provider_for_project(project)
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )
        print(f"{patches=}")

        patch_steps = []
        for patch in patches:
            print(f"Got patch with path: {patch.path}")
            patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                RunBackBoxBaseline(project, binary, result_post_fix="new")
            )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath,
                [RunBackBoxBaseline(project, binary, result_post_fix="old")] +
                patch_steps
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


################################################################################
# Overhead computation
################################################################################


class RunGenTracedWorkloadsOverhead(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "txt",
        reps=2
    ):
        super().__init__(
            project, binary, result_post_fix, report_file_ending, reps
        )

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            for rep in range(0, self._reps):
                for prj_command in workload_commands(
                    self.project, self._binary, [WorkloadCategory.EXAMPLE]
                ):
                    base = Path("/tmp/")
                    fake_tracefile_path = base / (
                        f"trace_{prj_command.command.label}_{rep}"
                        f".json"
                    )

                    time_report_file = tmp_dir / (
                        f"overhead_{prj_command.command.label}_{rep}"
                        f".{self._report_file_ending}"
                    )

                    with local.env(VARA_TRACE_FILE=fake_tracefile_path):
                        pb_cmd = prj_command.command.as_plumbum(
                            project=self.project
                        )
                        print(f"Running example {prj_command.command.label}")

                        timed_pb_cmd = time["-v", "-o", time_report_file,
                                            pb_cmd]

                        extra_options = get_extra_config_options(self.project)
                        with cleanup(prj_command):
                            timed_pb_cmd(
                                *extra_options,
                                retcode=self._binary.valid_exit_codes
                            )

        return StepResult.OK


def setup_actions_for_vara_overhead_experiment(
    experiment: FeatureExperiment, project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBase]
) -> tp.MutableSequence[actions.Step]:
    instr_type = FeatureInstrType.TEF

    project.cflags += experiment.get_vara_feature_cflags(project)

    threshold = 0 if project.DOMAIN.value is ProjectDomains.TEST else 100
    project.cflags += experiment.get_vara_tracing_cflags(
        instr_type, project=project, instruction_threshold=threshold
    )

    project.ldflags += experiment.get_vara_tracing_ldflags()

    # Add the required runtime extensions to the project(s).
    project.runtime_extension = bb_ext.run.RuntimeExtension(
        project, experiment
    ) << bb_ext.time.RunWithTime()

    # Add the required compiler extensions to the project(s).
    project.compiler_extension = bb_ext.compiler.RunCompiler(
        project, experiment
    ) << WithUnlimitedStackSize()

    # Add own error handler to compile step.
    project.compile = get_default_compile_error_wrapped(
        experiment.get_handle(), project, experiment.REPORT_SPEC.main_report
    )

    binary = project.binaries[0]
    if binary.type != BinaryType.EXECUTABLE:
        raise AssertionError("Experiment only works with executables.")

    result_filepath = create_new_success_result_filepath(
        experiment.get_handle(),
        experiment.get_handle().report_spec().main_report, project, binary,
        get_current_config_id(project)
    )

    analysis_actions = []

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath,
            [
                analysis_step(  # type: ignore
                    project, binary
                )
            ]
        )
    )
    analysis_actions.append(actions.Clean(project))

    return analysis_actions


class TEFProfileOverheadRunner(FeatureExperiment, shorthand="TEFo"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfilerO"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_overhead_experiment(
            self, project, FeatureInstrType.TEF, RunGenTracedWorkloadsOverhead
        )


class PIMProfileOverheadRunner(FeatureExperiment, shorthand="PIMo"):
    """Test runner for feature performance."""

    NAME = "RunPIMProfilerO"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_overhead_experiment(
            self, project, FeatureInstrType.PERF_INFLUENCE_TRACE,
            RunGenTracedWorkloadsOverhead
        )


class RunBackBoxBaselineOverhead(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        report_file_ending: str = "txt",
        reps=2
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__reps = reps

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Measure profiling overhead", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            for rep in range(0, self.__reps):
                for prj_command in workload_commands(
                    self.project, self.__binary, [WorkloadCategory.EXAMPLE]
                ):
                    time_report_file = tmp_dir / (
                        f"overhead_{prj_command.command.label}_{rep}"
                        f".{self.__report_file_ending}"
                    )

                    pb_cmd = prj_command.command.as_plumbum(
                        project=self.project
                    )
                    print(f"Running example {prj_command.command.label}")

                    timed_pb_cmd = time["-v", "-o", time_report_file, pb_cmd]

                    extra_options = get_extra_config_options(self.project)
                    with cleanup(prj_command):
                        timed_pb_cmd(
                            *extra_options,
                            retcode=self.__binary.valid_exit_codes
                        )

        return StepResult.OK


class BlackBoxOverheadBaseline(FeatureExperiment, shorthand="BBBaseO"):
    """Test runner for feature performance."""

    NAME = "GenBBBaselineO"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-flto", "-fuse-ld=lld", "-fno-omit-frame-pointer"]

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        binary = project.binaries[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath,
                [
                    RunBackBoxBaselineOverhead(  # type: ignore
                        project,
                        binary
                    ),
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

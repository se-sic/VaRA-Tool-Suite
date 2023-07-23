"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import textwrap
import typing as tp
from abc import abstractmethod
from pathlib import Path
from time import sleep

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult, Clean
from benchbuild.utils.cmd import time, rm, cp, numactl, sudo, bpftrace
from plumbum import local, BG
from plumbum.commands.modifiers import Future

from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReportAggregate,
)
from varats.experiment.experiment_util import (
    WithUnlimitedStackSize,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_current_config_id,
    get_default_compile_error_wrapped,
    get_extra_config_options,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
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
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReportAggregate
from varats.tools.research_tools.vara import VaRA
from varats.utils.git_util import ShortCommitHash

REPS = 3


class AnalysisProjectStepBase(OutputFolderStep):

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "json",
        reps=REPS
    ):
        super().__init__(project=project)
        self._binary = binary
        self._report_file_ending = report_file_ending
        self._file_name = file_name
        self._reps = reps

    @abstractmethod
    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        """Actual call implementation that gets a path to tmp_folder."""


class MPRTimeReportAggregate(
    MultiPatchReport[TimeReportAggregate], shorthand="MPRTRA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReportAggregate)


class MPRTEFAggregate(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRTEFA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReportAggregate)


class MPRPIMAggregate(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRPIMA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        # TODO: clean up report handling, we currently parse it as a TEFReport
        # as the file looks similar
        super().__init__(path, PerfInfluenceTraceReportAggregate)


class RunGenTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "json",
        reps=REPS
    ):
        super().__init__(project, binary, file_name, report_file_ending, reps)

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / self._file_name
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


class RunBPFTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunBPFTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "json",
        reps=REPS
    ):
        super().__init__(project, binary, file_name, report_file_ending, reps)

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / self._file_name
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

                            bpf_runner = self.attach_usdt_raw_tracing(
                                local_tracefile_path,
                                self.project.source_of_primary /
                                self._binary.path
                            )

                            with cleanup(prj_command):
                                pb_cmd(
                                    *extra_options,
                                    retcode=self._binary.valid_exit_codes
                                )

                            # wait for bpf script to exit
                            if bpf_runner:
                                bpf_runner.wait()

        return StepResult.OK

    @staticmethod
    def attach_usdt_raw_tracing(report_file: Path, binary: Path) -> Future:
        """Attach bpftrace script to binary to activate raw USDT probes."""
        bpftrace_script_location = Path(
            VaRA.install_location(),
            "share/vara/perf_bpf_tracing/RawUsdtTefMarker.bt"
        )
        bpftrace_script = bpftrace["-o", report_file, "-q",
                                   bpftrace_script_location, binary]
        bpftrace_script = bpftrace_script.with_env(BPFTRACE_PERF_RB_PAGES=4096)

        # Assertion: Can be run without sudo password prompt.
        bpftrace_cmd = sudo[bpftrace_script]
        # bpftrace_cmd = numactl["--cpunodebind=0", "--membind=0", bpftrace_cmd]

        bpftrace_runner = bpftrace_cmd & BG
        # give bpftrace time to start up, requires more time than regular USDT
        # script because a large number of probes increases the startup time
        sleep(10)
        return bpftrace_runner


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
                project,
                binary,
                file_name=MultiPatchReport.create_patched_report_name(
                    patch, "rep_measurements"
                )
            )
        )
        patch_steps.append(RevertPatch(project, patch))

    analysis_actions = []

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath, [
                analysis_step(
                    project,
                    binary,
                    file_name=MultiPatchReport.
                    create_baseline_report_name("rep_measurements")
                )
            ] + patch_steps
        )
    )
    analysis_actions.append(actions.Clean(project))

    return analysis_actions


class TEFProfileRunner(FeatureExperiment, shorthand="TEFp"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfiler"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

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

    REPORT_SPEC = ReportSpecification(MPRPIMAggregate)

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


class EbpfTraceTEFProfileRunner(FeatureExperiment, shorthand="ETEFp"):
    """Test runner for feature performance."""

    NAME = "RunEBPFTraceTEFProfiler"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

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
            self, project, FeatureInstrType.USDT_RAW, RunBPFTracedWorkloads
        )


class RunBackBoxBaseline(OutputFolderStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "txt",
        reps=REPS
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__reps = reps
        self.__file_name = file_name

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / self.__file_name
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

    REPORT_SPEC = ReportSpecification(MPRTimeReportAggregate)

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
                RunBackBoxBaseline(
                    project,
                    binary,
                    file_name=MPRTimeReportAggregate.create_patched_report_name(
                        patch, "rep_measurements"
                    )
                )
            )
            patch_steps.append(RevertPatch(project, patch))

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    RunBackBoxBaseline(
                        project,
                        binary,
                        file_name=MPRTimeReportAggregate.
                        create_baseline_report_name("rep_measurements")
                    )
                ] + patch_steps
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
        file_name: str,
        report_file_ending: str = "txt",
        reps=REPS
    ):
        super().__init__(project, binary, file_name, report_file_ending, reps)

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
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


class RunBPFTracedWorkloadsOverhead(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "txt",
        reps=REPS
    ):
        super().__init__(project, binary, file_name, report_file_ending, reps)

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
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

                        bpf_runner = RunBPFTracedWorkloads.attach_usdt_raw_tracing(
                            fake_tracefile_path,
                            self.project.source_of_primary / self._binary.path
                        )

                        with cleanup(prj_command):
                            timed_pb_cmd(
                                *extra_options,
                                retcode=self._binary.valid_exit_codes
                            )

                        # wait for bpf script to exit
                        if bpf_runner:
                            bpf_runner.wait()

        return StepResult.OK


def setup_actions_for_vara_overhead_experiment(
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

    analysis_actions = []

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath,
            [
                analysis_step(  # type: ignore
                    project, binary, "overhead"
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


class EbpfTraceTEFOverheadRunner(FeatureExperiment, shorthand="ETEFo"):
    """Test runner for feature performance."""

    NAME = "RunEBPFTraceTEFProfilerO"

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
            self, project, FeatureInstrType.USDT_RAW,
            RunBPFTracedWorkloadsOverhead
        )


class RunBackBoxBaselineOverhead(OutputFolderStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        report_file_ending: str = "txt",
        reps=REPS
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__reps = reps

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
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

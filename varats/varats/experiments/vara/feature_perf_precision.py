"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import tempfile
import textwrap
import typing as tp
from abc import abstractmethod
from pathlib import Path
from time import sleep

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult
from benchbuild.utils.cmd import time, cp, sudo, bpftrace
from plumbum import local, BG
from plumbum.commands.modifiers import Future

from varats.base.configuration import PatchConfiguration
from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReportAggregate,
)
from varats.experiment.experiment_util import (
    WithUnlimitedStackSize,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_default_compile_error_wrapped,
    ZippedExperimentSteps,
    OutputFolderStep,
    get_config_patch_steps,
)
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReportAggregate
from varats.tools.research_tools.vara import VaRA
from varats.utils.config import get_current_config_id, get_config
from varats.utils.git_util import ShortCommitHash

REPS = 3

IDENTIFIER_PATCH_TAG = 'perf_prec'


def perf_prec_workload_commands(
    project: VProject, binary: ProjectBinaryWrapper
) -> tp.List[ProjectCommand]:
    """Uniformly select the workloads that should be processed."""

    wl_commands = []

    if not project.name.startswith(
        "SynthIP"
    ) and project.name != "SynthSAFieldSensitivity":
        # Example commands from these CS are to "fast"
        wl_commands += workload_commands(
            project, binary, [WorkloadCategory.EXAMPLE]
        )

    wl_commands += workload_commands(project, binary, [WorkloadCategory.SMALL])

    wl_commands += workload_commands(project, binary, [WorkloadCategory.MEDIUM])

    return wl_commands


def select_project_binaries(project: VProject) -> tp.List[ProjectBinaryWrapper]:
    """Uniformly select the binaries that should be analyzed."""
    if project.name == "DunePerfRegression":
        config = get_config(project, PatchConfiguration)
        if not config:
            return []

        f_tags = {opt.value for opt in config.options()}

        grid_binary_map = {
            "YaspGrid": "poisson_yasp_q2_3d",
            "UGGrid": "poisson_ug_pk_2d",
            "ALUGrid": "poisson_alugrid"
        }

        for grid, binary_name in grid_binary_map.items():
            if grid in f_tags:
                return [
                    binary for binary in project.binaries
                    if binary.name == binary_name
                ]

    return [project.binaries[0]]


def get_extra_cflags(project: VProject) -> tp.List[str]:
    """Get additional cflags for some projects."""
    extra_flags = []

    if project.name == "DunePerfRegression":
        extra_flags += ["-pthread"]

    if project.name in ["DunePerfRegression", "HyTeg"]:
        # Disable phasar for dune as the analysis cannot handle dunes size
        extra_flags += ["-fvara-disable-phasar"]

    return extra_flags


def get_threshold(project: VProject) -> int:
    """Get the project specific instrumentation threshold."""
    if project.DOMAIN is ProjectDomains.TEST:
        if project.name in [
            "SynthSAFieldSensitivity", "SynthIPRuntime", "SynthIPTemplate",
            "SynthIPTemplate2", "SynthIPCombined"
        ]:
            # Don't instrument everything for these synthetic projects
            return 10

        return 0

    if project.name in ["HyTeg", "PicoSATLoadTime"]:
        return 0

    return 100


class AnalysisProjectStepBase(OutputFolderStep):
    """Base class for project steps."""

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        file_name: str,
        report_file_ending: str = "json",
        reps: int = REPS
    ) -> None:
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
    """Multi-patch wrapper report for time aggregates."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReportAggregate)


class MPRTEFAggregate(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRTEFA", file_type=".zip"
):
    """Multi-patch wrapper report for tef aggregates."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReportAggregate)


class MPRPIMAggregate(
    MultiPatchReport[TEFReportAggregate], shorthand="MPRPIMA", file_type=".zip"
):
    """Multi-patch wrapper report for tef aggregates."""

    def __init__(self, path: Path) -> None:
        # TODO: clean up report handling, we currently parse it as a TEFReport
        # as the file looks similar
        super().__init__(
            path,
            PerfInfluenceTraceReportAggregate  # type: ignore
        )


class RunGenTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

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
                    for prj_command in perf_prec_workload_commands(
                        self.project, self._binary
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

                            with cleanup(prj_command):
                                pb_cmd(retcode=self._binary.valid_exit_codes)

        return StepResult.OK


class RunBPFTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunBPFTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

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
            with tempfile.TemporaryDirectory() as non_nfs_tmp_dir:
                with ZippedReportFolder(zip_tmp_dir) as reps_tmp_dir:
                    for rep in range(0, self._reps):
                        for prj_command in perf_prec_workload_commands(
                            self.project, self._binary
                        ):
                            local_tracefile_path = Path(reps_tmp_dir) / (
                                f"trace_{prj_command.command.label}_{rep}"
                                f".{self._report_file_ending}"
                            )

                            with local.env(
                                VARA_TRACE_FILE=local_tracefile_path
                            ):
                                adapted_binary_location = Path(
                                    non_nfs_tmp_dir
                                ) / self._binary.name

                                pb_cmd = \
                                    prj_command.command.as_plumbum_wrapped_with(
                                        adapted_binary_location=
                                        adapted_binary_location,
                                        project=self.project
                                    )

                                bpf_runner = \
                                    self.attach_usdt_raw_tracing(
                                        local_tracefile_path,
                                        adapted_binary_location,
                                        Path(non_nfs_tmp_dir)
                                    )

                                with cleanup(prj_command):
                                    print(
                                        "Running example "
                                        f"{prj_command.command.label}"
                                    )
                                    pb_cmd(
                                        retcode=self._binary.valid_exit_codes
                                    )

                                # wait for bpf script to exit
                                if bpf_runner:
                                    bpf_runner.wait()

        return StepResult.OK

    @staticmethod
    def attach_usdt_raw_tracing(
        report_file: Path, binary: Path, non_nfs_tmp_dir: Path
    ) -> Future:
        """Attach bpftrace script to binary to activate raw USDT probes."""
        orig_bpftrace_script_location = Path(
            VaRA.install_location(),
            "share/vara/perf_bpf_tracing/RawUsdtTefMarker.bt"
        )
        # Store bpftrace script in a local tmp dir that is not on nfs
        bpftrace_script_location = non_nfs_tmp_dir / "RawUsdtTefMarker.bt"
        cp(orig_bpftrace_script_location, bpftrace_script_location)

        bpftrace_script = bpftrace["-o", report_file, "--no-warnings", "-q",
                                   bpftrace_script_location, binary]
        bpftrace_script = bpftrace_script.with_env(BPFTRACE_PERF_RB_PAGES=8192)

        # Assertion: Can be run without sudo password prompt.
        bpftrace_cmd = sudo[bpftrace_script]

        bpftrace_runner = bpftrace_cmd & BG
        # give bpftrace time to start up, requires more time than regular USDT
        # script because a large number of probes increases the startup time
        sleep(10)
        return bpftrace_runner


class RunBCCTracedWorkloads(AnalysisProjectStepBase):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunBCCTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

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
                    for prj_command in perf_prec_workload_commands(
                        self.project, self._binary
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

                            bpf_runner = self.attach_usdt_bcc(
                                local_tracefile_path,
                                self.project.source_of_primary /
                                self._binary.path
                            )

                            with cleanup(prj_command):
                                pb_cmd(retcode=self._binary.valid_exit_codes)

                            # wait for bpf script to exit
                            if bpf_runner:
                                bpf_runner.wait()

        return StepResult.OK

    @staticmethod
    def attach_usdt_bcc(report_file: Path, binary: Path) -> Future:
        """Attach bcc script to binary to activate USDT probes."""
        bcc_script_location = Path(
            VaRA.install_location(),
            "share/vara/perf_bpf_tracing/UsdtTefMarker.py"
        )
        bcc_script = local[str(bcc_script_location)]

        # Assertion: Can be run without sudo password prompt.
        bcc_cmd = bcc_script["--output_file", report_file, "--no_poll",
                             "--executable", binary]
        print(f"{bcc_cmd=}")
        bcc_cmd = sudo[bcc_cmd]

        bcc_runner = bcc_cmd & BG
        sleep(3)  # give bcc script time to start up
        return bcc_runner


AnalysisProjectStepBaseTy = tp.TypeVar(
    "AnalysisProjectStepBaseTy", bound=AnalysisProjectStepBase
)


def setup_actions_for_vara_experiment(
    experiment: FeatureExperiment,
    project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBaseTy],
    report_type=MultiPatchReport
) -> tp.MutableSequence[actions.Step]:
    """Sets up actions for a given perf precision experiment."""

    project.cflags += experiment.get_vara_feature_cflags(project)

    threshold = get_threshold(project)
    project.cflags += experiment.get_vara_tracing_cflags(
        instr_type,
        project=project,
        save_temps=True,
        instruction_threshold=threshold
    )

    project.cflags += get_extra_cflags(project)

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

    # TODO: change to multiple binaries
    binary = select_project_binaries(project)[0]
    if binary.type != BinaryType.EXECUTABLE:
        raise AssertionError("Experiment only works with executables.")

    result_filepath = create_new_success_result_filepath(
        experiment.get_handle(),
        experiment.get_handle().report_spec().main_report, project, binary,
        get_current_config_id(project)
    )

    patch_provider = PatchProvider.get_provider_for_project(type(project))
    patches = patch_provider.get_patches_for_revision(
        ShortCommitHash(project.version_of_primary)
    )[IDENTIFIER_PATCH_TAG]

    patch_steps = []
    for patch in patches:
        patch_steps.append(ApplyPatch(project, patch))
        patch_steps.append(ReCompile(project))
        patch_steps.append(
            analysis_step(
                project,
                binary,
                file_name=report_type.create_patched_report_name(
                    patch, "rep_measurements"
                )
            )
        )
        patch_steps.append(RevertPatch(project, patch))

    analysis_actions = get_config_patch_steps(project)

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath, [
                analysis_step(
                    project,
                    binary,
                    file_name=report_type.
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
            self,
            project,
            FeatureInstrType.TEF,
            RunGenTracedWorkloads  # type: ignore[type-abstract]
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
            self,
            project,
            FeatureInstrType.PERF_INFLUENCE_TRACE,
            RunGenTracedWorkloads  # type: ignore[type-abstract]
        )


class EbpfTraceTEFProfileRunner(FeatureExperiment, shorthand="ETEFp"):
    """Test runner for feature performance."""

    NAME = "RunEBPFTraceTEFProfiler"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

    CONTAINER = ContainerImage().run('apt', 'install', '-y', 'bpftrace')

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
            self,
            project,
            FeatureInstrType.USDT_RAW,
            RunBPFTracedWorkloads  # type: ignore[type-abstract]
        )


class BCCTEFProfileRunner(FeatureExperiment, shorthand="BCCp"):
    """Test runner for feature performance."""

    NAME = "RunBCCTEFProfiler"

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
            self,
            project,
            FeatureInstrType.USDT,
            RunBCCTracedWorkloads  # type: ignore[type-abstract]
        )


class RunBlackBoxBaseline(AnalysisProjectStepBase):  # type: ignore
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
        reps: int = REPS
    ) -> None:
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
                    for prj_command in perf_prec_workload_commands(
                        self.project, self._binary
                    ):
                        time_report_file = Path(reps_tmp_dir) / (
                            f"baseline_{prj_command.command.label}_{rep}"
                            f".{self._report_file_ending}"
                        )

                        print(f"Running example {prj_command.command.label}")

                        with cleanup(prj_command):
                            pb_cmd = \
                                prj_command.command.as_plumbum_wrapped_with(
                                    time["-v", "-o", time_report_file],
                                    project=self.project
                                )
                            pb_cmd(retcode=self._binary.valid_exit_codes)

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
        return setup_actions_for_vara_experiment(
            self, project, FeatureInstrType.NONE, RunBlackBoxBaseline,
            MPRTimeReportAggregate
        )


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
        reps: int = REPS
    ) -> None:
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
                for prj_command in perf_prec_workload_commands(
                    self.project, self._binary
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
                        print(f"Running example {prj_command.command.label}")

                        with cleanup(prj_command):
                            pb_cmd = \
                                prj_command.command.as_plumbum_wrapped_with(
                                    time["-v", "-o", time_report_file],
                                    project=self.project
                                )
                            pb_cmd(retcode=self._binary.valid_exit_codes)

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
        reps: int = REPS
    ) -> None:
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
            with tempfile.TemporaryDirectory() as non_nfs_tmp_dir:
                for rep in range(0, self._reps):
                    for prj_command in perf_prec_workload_commands(
                        self.project, self._binary
                    ):
                        base = Path(non_nfs_tmp_dir)
                        fake_tracefile_path = base / (
                            f"trace_{prj_command.command.label}_{rep}"
                            f".json"
                        )

                        time_report_file = tmp_dir / (
                            f"overhead_{prj_command.command.label}_{rep}"
                            f".{self._report_file_ending}"
                        )

                        with local.env(VARA_TRACE_FILE=fake_tracefile_path):
                            adapted_binary_location = Path(
                                non_nfs_tmp_dir
                            ) / self._binary.name

                            pb_cmd = \
                                prj_command.command.as_plumbum_wrapped_with(
                                    time["-v", "-o", time_report_file],
                                    adapted_binary_location,
                                    project=self.project
                                )

                            bpf_runner = \
                                RunBPFTracedWorkloads.attach_usdt_raw_tracing(
                                    fake_tracefile_path, \
                                    adapted_binary_location,
                                    Path(non_nfs_tmp_dir)
                                )

                            with cleanup(prj_command):
                                print(
                                    "Running example "
                                    f"{prj_command.command.label}"
                                )
                                pb_cmd(retcode=self._binary.valid_exit_codes)

                            # wait for bpf script to exit
                            if bpf_runner:
                                bpf_runner.wait()

        return StepResult.OK


class RunBCCTracedWorkloadsOverhead(AnalysisProjectStepBase):  # type: ignore
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
        reps: int = REPS
    ) -> None:
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
                for prj_command in perf_prec_workload_commands(
                    self.project, self._binary
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

                        timed_pb_cmd = time["-v", "-o", time_report_file, "--",
                                            pb_cmd]

                        bpf_runner = RunBCCTracedWorkloads.attach_usdt_bcc(
                            fake_tracefile_path,
                            self.project.source_of_primary / self._binary.path
                        )

                        with cleanup(prj_command):
                            timed_pb_cmd(retcode=self._binary.valid_exit_codes)

                        # wait for bpf script to exit
                        if bpf_runner:
                            bpf_runner.wait()

        return StepResult.OK


def setup_actions_for_vara_overhead_experiment(
    experiment: FeatureExperiment, project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBase]
) -> tp.MutableSequence[actions.Step]:
    """Sets up actions for a given perf overhead experiment."""
    project.cflags += experiment.get_vara_feature_cflags(project)

    threshold = get_threshold(project)
    project.cflags += experiment.get_vara_tracing_cflags(
        instr_type, project=project, instruction_threshold=threshold
    )

    project.cflags += get_extra_cflags(project)

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

    # TODO: change to multiple binaries
    binary = select_project_binaries(project)[0]
    if binary.type != BinaryType.EXECUTABLE:
        raise AssertionError("Experiment only works with executables.")

    result_filepath = create_new_success_result_filepath(
        experiment.get_handle(),
        experiment.get_handle().report_spec().main_report, project, binary,
        get_current_config_id(project)
    )

    analysis_actions = get_config_patch_steps(project)

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

    CONTAINER = ContainerImage().run('apt', 'install', '-y', 'bpftrace')

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


class BccTraceTEFOverheadRunner(FeatureExperiment, shorthand="BCCo"):
    """Test runner for feature performance."""

    NAME = "RunBCCTEFProfilerO"

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
            self, project, FeatureInstrType.USDT, RunBCCTracedWorkloadsOverhead
        )


class RunBlackBoxBaselineOverhead(AnalysisProjectStepBase):  # type: ignore
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
        reps: int = REPS
    ) -> None:
        super().__init__(project, binary, file_name, report_file_ending, reps)

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Measure profiling overhead", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            for rep in range(0, self._reps):
                for prj_command in perf_prec_workload_commands(
                    self.project, self._binary
                ):
                    time_report_file = tmp_dir / (
                        f"overhead_{prj_command.command.label}_{rep}"
                        f".{self._report_file_ending}"
                    )

                    with cleanup(prj_command):
                        print(f"Running example {prj_command.command.label}")
                        pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                            time["-v", "-o", time_report_file],
                            project=self.project
                        )

                        pb_cmd(retcode=self._binary.valid_exit_codes)

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
        return setup_actions_for_vara_overhead_experiment(
            self, project, FeatureInstrType.NONE, RunBlackBoxBaselineOverhead
        )

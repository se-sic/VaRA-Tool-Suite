"""Multiple experiments for tracing feature performance using VaRA's TEF and
USDT instrumentation."""
import typing as tp
from enum import Enum
from pathlib import Path
from time import sleep

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.utils.actions import ProjectStep, Step, StepResult
from benchbuild.utils.cmd import time, cp, numactl, sudo, bpftrace
from plumbum import BG, local
from plumbum.commands.modifiers import Future

from varats.data.reports.compiled_binary_report import CompiledBinaryReport
from varats.experiment.experiment_util import (
    ExperimentHandle,
    ZippedReportFolder,
    create_new_success_result_filepath,
)
from varats.experiment.workload_util import workload_commands, WorkloadCategory
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReport
from varats.tools.research_tools.vara import VaRA


class BPFProgType(Enum):
    """
    Kind of front-end to use for the eBPF tracing program.

    BCC is lower-level and therefore exposes more options giving the opportunity
    to reduce overhead. BCC programs are much harder to understand and write
    though so using bpftrace is recommended except when dealing with very high
    event frequencies.
    """
    NONE = 0
    BPFTRACE = 1
    BCC = 2


class TraceFeaturePerfAndTime(ProjectStep):  # type: ignore
    """
    Step to trace feature performance and collect execution time using GNU Time.
    Additionally, compiled binaries are copied to the results directory for
    further investigation afterwards.

    Each binary is executed `num_iterations` times. A `TimeReportAggregate`
    is produced for each binary, which contains the execution time of each
    iteration. Additionally, a single `TEFReport` is produced per binary
    containing the information of the last iteration. Trace files can get
    quite large which is why we decided to not use a `TEFReportAggregate`
    for now.

    IMPORTANT: Attaching eBPF tracing programs requires root privileges,
    make sure that bpftrace and VaRA's BCC Python script can be invoked with
    sudo without having to enter the passwort first. This can be achieved by
    adding a file to `/etc/sudoers.d/`.
    """

    NAME = "TraceFeaturePerfWithTime"
    DESCRIPTION = "Trace feature performance and collect total execution time"

    project: VProject

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
        instrumentation: FeatureInstrType,
        num_iterations: int = 2,
        bpf_prog_type: BPFProgType = BPFProgType.BPFTRACE
    ):
        super().__init__(project=project)
        self.experiment_handle = experiment_handle
        self.instrumentation = instrumentation
        self.bpf_prog_type = bpf_prog_type
        self.num_iterations = num_iterations

    def __call__(self) -> StepResult:
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            # copy binary to allow investigation of instrumentation
            binary_report = create_new_success_result_filepath(
                self.experiment_handle, CompiledBinaryReport, self.project,
                binary
            )
            cp(Path(self.project.source_of_primary, binary.path), binary_report)

            # get workload to use
            workloads = workload_commands(
                self.project, binary, [WorkloadCategory.MEDIUM]
            )
            if len(workloads) == 0:
                print(
                    f"No workload for project={self.project.name} "
                    f"binary={binary.name}. Skipping."
                )
                continue
            if len(workloads) > 1:
                raise RuntimeError(
                    "Currently, only a single workload is supported. "
                    f"project={self.project.name} binary={binary.name}"
                )
            workload = workloads[0]

            # report paths
            tef_report = create_new_success_result_filepath(
                self.experiment_handle, TEFReport, self.project, binary
            )
            time_report_agg = create_new_success_result_filepath(
                self.experiment_handle, TimeReportAggregate, self.project,
                binary
            )

            # execute and trace binary
            with ZippedReportFolder(
                time_report_agg.full_path()
            ) as time_report_dir, local.cwd(self.project.builddir):
                for i in range(self.num_iterations):
                    print(
                        f"Binary={binary.name} Progress "
                        f"{i}/{self.num_iterations}",
                        flush=True  # print immediately
                    )

                    time_report_path = Path(
                        time_report_dir, f"iteration_{i}.{TimeReport.FILE_TYPE}"
                    )

                    with local.env(VARA_TRACE_FILE=tef_report.full_path()), \
                        local.cwd(self.project.builddir):
                        run_cmd = workload.command.as_plumbum(
                            project=self.project
                        )
                        run_cmd = time["-v", "-o", time_report_path, run_cmd]
                        # Bind run_cmd and later bpf runner to the same NUMA
                        # node. This is done to reduce possible execution time
                        # influences from running the two processes on different
                        # NUMA nodes.
                        run_cmd = numactl["--cpunodebind=0", "--membind=0",
                                          run_cmd]

                        # Attach BPF program to USDT probes. For the regular
                        # USDT instrumentation, VaRA offers a lower level BCC
                        # program with possibly lower overhead instead of the
                        # one based on bpftrace. If unsure, use bpftrace because
                        # it's much easier to understand and work with.
                        bpf_runner = None
                        if self.instrumentation is FeatureInstrType.USDT_RAW:
                            if self.bpf_prog_type is BPFProgType.BCC:
                                raise RuntimeError(
                                    "BCC is unsupported for raw USDT probes."
                                )
                            if self.bpf_prog_type is BPFProgType.BPFTRACE:
                                bpf_runner = self.attach_usdt_raw_tracing(
                                    tef_report.full_path(),
                                    self.project.source_of_primary / binary.path
                                )
                        elif self.instrumentation is FeatureInstrType.USDT:
                            if self.bpf_prog_type is BPFProgType.BCC:
                                bpf_runner = self.attach_usdt_bcc(
                                    tef_report.full_path(),
                                    self.project.source_of_primary / binary.path
                                )
                            elif self.bpf_prog_type is BPFProgType.BPFTRACE:
                                bpf_runner = self.attach_usdt_bpftrace(
                                    tef_report.full_path(),
                                    self.project.source_of_primary / binary.path
                                )

                        # run binary with workload in foreground
                        with cleanup(workload):
                            bb.watch(run_cmd)()

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
        bcc_cmd = sudo[bcc_cmd]
        bcc_cmd = numactl["--cpunodebind=0", "--membind=0", bcc_cmd]

        bcc_runner = bcc_cmd & BG
        sleep(3)  # give bcc script time to start up
        return bcc_runner

    @staticmethod
    def attach_usdt_bpftrace(report_file: Path, binary: Path) -> Future:
        """Attach bpftrace script to binary to activate USDT probes."""
        bpftrace_script_location = Path(
            VaRA.install_location(),
            "share/vara/perf_bpf_tracing/UsdtTefMarker.bt"
        )
        bpftrace_script = bpftrace["-o", report_file, "-q",
                                   bpftrace_script_location, binary]
        bpftrace_script = bpftrace_script.with_env(BPFTRACE_PERF_RB_PAGES=4096)

        # Assertion: Can be run without sudo password prompt.
        bpftrace_cmd = sudo[bpftrace_script]
        bpftrace_cmd = numactl["--cpunodebind=0", "--membind=0", bpftrace_cmd]

        bpftrace_runner = bpftrace_cmd & BG
        sleep(3)  # give bpftrace time to start up
        return bpftrace_runner

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
        bpftrace_cmd = numactl["--cpunodebind=0", "--membind=0", bpftrace_cmd]

        bpftrace_runner = bpftrace_cmd & BG
        # give bpftrace time to start up, requires more time than regular USDT
        # script because a large number of probes increases the startup time
        sleep(10)
        return bpftrace_runner


class FeaturePerfTracingDry(FeatureExperiment, shorthand="FPT_Dry"):
    """Capture total execution time when running dry (inactive tracing) and
    without any instrumentation."""

    NAME = "FeaturePerfTracingDry"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.NONE
        return self.get_common_tracing_actions(
            project,
            instr_type,
            [TraceFeaturePerfAndTime(project, self.get_handle(), instr_type)],
            instruction_threshold=0
        )


class FeaturePerfTracingDryUsdt(FeatureExperiment, shorthand="FPT_Dry_USDT"):
    """Capture total execution time of VaRA's inactive regular USDT
    instrumentation."""

    NAME = "FeaturePerfTracingDryUsdt"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.USDT
        return self.get_common_tracing_actions(
            project,
            instr_type, [
                TraceFeaturePerfAndTime(
                    project,
                    self.get_handle(),
                    instr_type,
                    bpf_prog_type=BPFProgType.NONE
                )
            ],
            instruction_threshold=0
        )


class FeaturePerfTracingDryRawUsdt(
    FeatureExperiment, shorthand="FPT_Dry_RawUSDT"
):
    """Capture total execution time of VaRA's inactive raw USDT
    instrumentation."""

    NAME = "FeaturePerfTracingDryRawUsdt"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.USDT_RAW
        return self.get_common_tracing_actions(
            project,
            instr_type, [
                TraceFeaturePerfAndTime(
                    project,
                    self.get_handle(),
                    instr_type,
                    bpf_prog_type=BPFProgType.NONE
                )
            ],
            instruction_threshold=0
        )


class FeaturePerfTracingTef(FeatureExperiment, shorthand="FPT_TEF"):
    """Trace feature performance and capture total execution time of VaRA's TEF
    (Trace Event File) instrumentation."""

    NAME = "FeaturePerfTracingTef"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.TEF
        return self.get_common_tracing_actions(
            project,
            instr_type,
            [TraceFeaturePerfAndTime(project, self.get_handle(), instr_type)],
            instruction_threshold=0
        )


class FeaturePerfTracingTefUsdt(FeatureExperiment, shorthand="FPT_TEF_USDT"):
    """
    Trace feature performance using VaRA's regular USDT instrumentation and
    attach the included BPF program based on bpftrace to produce a TEF.

    Additionally, measure total execution time.
    """

    NAME = "FeaturePerfTracingTefUsdt"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.USDT
        return self.get_common_tracing_actions(
            project,
            instr_type,
            [TraceFeaturePerfAndTime(project, self.get_handle(), instr_type)],
            instruction_threshold=0
        )


class FeaturePerfTracingTefUsdtBcc(
    FeatureExperiment, shorthand="FPT_TEF_USDT_BCC"
):
    """
    Trace feature performance using VaRA's regular USDT instrumentation and
    attach the included BPF program based on the lower-level BCC language to
    produce a TEF.

    Additionally, measure total execution time.
    """

    NAME = "FeaturePerfTracingTefUsdtBcc"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.USDT
        return self.get_common_tracing_actions(
            project,
            instr_type, [
                TraceFeaturePerfAndTime(
                    project,
                    self.get_handle(),
                    instr_type,
                    bpf_prog_type=BPFProgType.BCC
                )
            ],
            instruction_threshold=0
        )


class FeaturePerfTracingTefRawUsdt(
    FeatureExperiment, shorthand="FPT_TEF_RawUSDT"
):
    """
    Trace feature performance using VaRA's raw USDT instrumentation and attach
    the included BPF program based on bpftrace to produce a TEF.

    Additionally, measure total execution time.
    """

    NAME = "FeaturePerfTracingTefRawUsdt"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, TEFReport, CompiledBinaryReport
    )

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        instr_type = FeatureInstrType.USDT_RAW
        return self.get_common_tracing_actions(
            project,
            instr_type,
            [TraceFeaturePerfAndTime(project, self.get_handle(), instr_type)],
            instruction_threshold=0
        )

"""Contains multiple experiments for running different feature performance
analysis approaches and enables their comparison."""
import typing as tp
from pathlib import Path
from time import sleep

from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.extensions import time as bbtime
from benchbuild.utils import actions
from benchbuild.utils.cmd import time, cp, mkdir
from plumbum import BG, FG, local
from plumbum.commands.modifiers import Future

from varats.experiment.experiment_util import (
    ExperimentHandle,
    ZippedReportFolder,
    get_varats_result_folder,
    VersionExperiment,
)
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.provider.workload.workload_provider import WorkloadProvider
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import FileStatusExtension, ReportSpecification
from varats.report.tef_report import TEFReport
from varats.tools.research_tools.vara import VaRA


class TraceFeaturePerfWithTime(actions.Step):  # type: ignore
    """See `DESCRIPTION`."""

    NAME = "TraceFeaturePerfWithTime"
    DESCRIPTION = '''Traces the feature performance of the specified binaries
                  when executing them on predefined workloads. Also collects
                  runtime information using gnu time.'''

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        num_iterations: int,
        attach_bpf: bool = False
    ):
        super().__init__(obj=project, action_fn=self.run)
        self._experiment_handle = experiment_handle
        self._num_iterations = num_iterations
        self._attach_bpf = attach_bpf

    def run(self) -> actions.StepResult:
        """Action function for this step."""
        project: Project = self.obj

        vara_result_folder = get_varats_result_folder(project)
        binary: ProjectBinaryWrapper

        for binary in project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            # Copy binary to allow further investigation after experiment.
            binaries_dir = Path("/tmp/traced_feature_perf_binaries")
            mkdir("-p", binaries_dir)
            cp(
                Path(project.source_of_primary, binary.path), binaries_dir /
                (f"{binary.name}_" + self._experiment_handle.shorthand())
            )

            # Get workload to use.
            # pylint: disable=W0511
            # TODO (se-sic/VaRA#841): refactor to bb workloads if possible
            workload_provider = WorkloadProvider.create_provider_for_project(
                project
            )
            if not workload_provider:
                print(
                    f"No workload provider for project={project.name}. " \
                    "Skipping."
                )
                return actions.StepResult.CAN_CONTINUE
            workload = workload_provider.get_workload_for_binary(binary.name)
            if workload is None:
                print(
                    f"No workload for project={project.name} " \
                        f"binary={binary.name}. Skipping."
                )
                continue

            # Assemble Path for TEF report.
            tef_report_file_name = self._experiment_handle.get_file_name(
                TEFReport.shorthand(),
                project_name=project.name,
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.SUCCESS
            )

            tef_report_file = Path(
                vara_result_folder, str(tef_report_file_name)
            )

            # Assemble Path for time report.
            time_report_file_name = self._experiment_handle.get_file_name(
                TimeReportAggregate.shorthand(),
                project_name=project.name,
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.SUCCESS
            )

            time_report_file = Path(
                vara_result_folder, str(time_report_file_name)
            )

            # Execute and trace binary.
            with ZippedReportFolder(time_report_file) as time_tmp:
                for i in range(self._num_iterations):

                    # Print progress.
                    print(
                        f"Binary={binary.name} Progress "
                        f"{i}/{self._num_iterations}",
                        flush=True
                    )

                    # Generate full time report filename.
                    time_report_file = Path(
                        time_tmp, f"time_iteration_{i}.{TimeReport.FILE_TYPE}"
                    )

                    with local.cwd(project.source_of_primary), \
                            local.env(VARA_TRACE_FILE=tef_report_file):
                        run_cmd = binary[workload]
                        run_cmd = time["-v", "-o", time_report_file, run_cmd]

                        # Attach bcc script to activate USDT probes.
                        bcc_runner: Future
                        if self._attach_bpf:
                            bcc_runner = \
                                TraceFeaturePerfWithTime.attach_bcc_tef_script(
                                    tef_report_file, binary.path
                                )

                        # Run binary.
                        run_cmd & FG  # pylint: disable=W0104

                        # Wait for bcc running in background to exit.
                        if self._attach_bpf:
                            bcc_runner.wait()

        return actions.StepResult.OK

    @staticmethod
    def attach_bcc_tef_script(report_file: Path, binary: Path) -> Future:
        """Attach bcc script to binary to activate USDT probes."""
        bcc_script_location = Path(
            VaRA.install_location(),
            "share/vara/perf_bpf_tracing/UsdtTefMarker.py"
        )
        bcc_script = local[str(bcc_script_location)]

        # Assertion: Can be run without sudo password prompt.
        bcc_cmd = bcc_script["--output_file", report_file, "--no_poll",
                             "--executable", binary]
        with local.as_root():
            bcc_runner = bcc_cmd & BG
            sleep(3)  # give bcc script time to start up
            return bcc_runner


class FeaturePerfAnalysisDry(VersionExperiment, shorthand="FPA_Dry"):
    """Captures baseline runtime (without any instrumentation)."""

    NAME = "FeaturePerfAnalysisDry"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate, TEFReport)

    def __init__(
        self,
        *args: tp.Any,
        trace_binaries: bool = False,
        instrument_usdt: bool = False,
        **kwargs: tp.Any
    ):
        super().__init__(*args, **kwargs)

        self._trace_binaries = trace_binaries
        self._instrument_usdt = instrument_usdt

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add tracing markers.
        if self._trace_binaries or self._instrument_usdt:
            fm_provider = FeatureModelProvider.create_provider_for_project(
                project
            )
            if fm_provider is None:
                raise Exception("Could not get FeatureModelProvider!")

            fm_path = fm_provider.get_feature_model_path(
                project.version_of_primary
            )
            if fm_path is None or not fm_path.exists():
                raise FeatureModelNotFound(project, fm_path)

            # Sets vara tracing flags
            project.cflags += [
                "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}",
                "-fsanitize=vara"
            ]
            if self._instrument_usdt:
                project.cflags += ["-fvara-instr=usdt"]
            elif self._trace_binaries:
                project.cflags += ["-fvara-instr=trace_event"]

            project.cflags += ["-flto", "-fuse-ld=lld"]
            project.ldflags += ["-flto"]
        # Enable compiler optimizations for case without instrumentation.
        else:
            project.cflags += ["-O3"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << bbtime.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            TraceFeaturePerfWithTime(
                project, self.get_handle(), 1, self._trace_binaries and
                self._instrument_usdt
            )
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class FeaturePerfAnalysisDryUsdt(
    FeaturePerfAnalysisDry, shorthand="FPA_Dry_USDT"
):
    """Captures baseline runtime for inactive probes instrumented by VaRA's USDT
    feature performance analysis instrumentation."""

    NAME = "FeaturePerfAnalysisDryUsdt"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any):
        super().__init__(
            *args, trace_binaries=False, instrument_usdt=True, **kwargs
        )


class FeaturePerfAnalysisTef(FeaturePerfAnalysisDry, shorthand="FPA_TEF"):
    """Traces feature performance using VaRA's TEF instrumentation."""

    NAME = "FeaturePerfAnalysisTef"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any):
        super().__init__(
            *args, trace_binaries=True, instrument_usdt=False, **kwargs
        )


class FeaturePerfAnalysisTefUsdt(
    FeaturePerfAnalysisDry, shorthand="FPA_TEF_USDT"
):
    """Traces feature performance using VaRA's USDT instrumentation and attaches
    to these probes via a BPF script to generate a TEF."""

    NAME = "FeaturePerfAnalysisTefUsdt"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any):
        super().__init__(
            *args, trace_binaries=True, instrument_usdt=True, **kwargs
        )

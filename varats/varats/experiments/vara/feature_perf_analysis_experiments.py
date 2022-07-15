"""Contains multiple experiments for running different feature performance
analysis approaches and enables their comparison."""
import typing as tp
from pathlib import Path
from time import sleep

from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import time, cp, mkdir
from plumbum import BG, FG, local
from plumbum.commands.modifiers import Future

from varats.experiment.experiment_util import (
    ExperimentHandle,
    ZippedReportFolder,
    get_varats_result_folder,
)
from varats.experiment.feature_perf_experiments import (
    FeaturePerfExperiment,
    InstrumentationType,
)
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
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
        attach_bpf: bool = False
    ):
        super().__init__(obj=project, action_fn=self.run)
        self._experiment_handle = experiment_handle
        self._attach_bpf = attach_bpf
        self._num_iterations = 1

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


class FeaturePerfAnalysisDry(FeaturePerfExperiment, shorthand="FPA_Dry"):
    """Captures baseline runtime (without any instrumentation)."""

    NAME = "FeaturePerfAnalysisDry"
    REPORT_SPEC = ReportSpecification(TimeReportAggregate, TEFReport)

    def actions_for_project(
        self,
        project: Project,
        instrumentation: InstrumentationType = InstrumentationType.NONE,
        analysis_actions: tp.Optional[tp.Iterable[actions.Step]] = None,
        use_feature_model: bool = False
    ) -> tp.MutableSequence[actions.Step]:

        analysis_actions = [
            TraceFeaturePerfWithTime(project, self.get_handle())
        ]
        return super().actions_for_project(
            project, instrumentation, analysis_actions, use_feature_model
        )


class FeaturePerfAnalysisDryUsdt(
    FeaturePerfExperiment, shorthand="FPA_Dry_USDT"
):
    """Captures baseline runtime for inactive probes instrumented by VaRA's USDT
    feature performance analysis instrumentation."""

    NAME = "FeaturePerfAnalysisDryUsdt"
    REPORT_SPEC = ReportSpecification(TimeReportAggregate, TEFReport)

    def actions_for_project(
        self,
        project: Project,
        instrumentation: InstrumentationType = InstrumentationType.USDT,
        analysis_actions: tp.Optional[tp.Iterable[actions.Step]] = None,
        use_feature_model: bool = True
    ) -> tp.MutableSequence[actions.Step]:

        analysis_actions = [
            TraceFeaturePerfWithTime(project, self.get_handle())
        ]
        return super().actions_for_project(
            project, instrumentation, analysis_actions, use_feature_model
        )


class FeaturePerfAnalysisTef(FeaturePerfExperiment, shorthand="FPA_TEF"):
    """Traces feature performance using VaRA's TEF instrumentation."""

    NAME = "FeaturePerfAnalysisTef"
    REPORT_SPEC = ReportSpecification(TimeReportAggregate, TEFReport)

    def actions_for_project(
        self,
        project: Project,
        instrumentation: InstrumentationType = InstrumentationType.TEF,
        analysis_actions: tp.Optional[tp.Iterable[actions.Step]] = None,
        use_feature_model: bool = True
    ) -> tp.MutableSequence[actions.Step]:

        analysis_actions = [
            TraceFeaturePerfWithTime(project, self.get_handle())
        ]
        return super().actions_for_project(
            project, instrumentation, analysis_actions, use_feature_model
        )


class FeaturePerfAnalysisTefUsdt(
    FeaturePerfExperiment, shorthand="FPA_TEF_USDT"
):
    """Traces feature performance using VaRA's USDT instrumentation and attaches
    to these probes via a BPF script to generate a TEF."""

    NAME = "FeaturePerfAnalysisTefUsdt"
    REPORT_SPEC = ReportSpecification(TimeReportAggregate, TEFReport)

    def actions_for_project(
        self,
        project: Project,
        instrumentation: InstrumentationType = InstrumentationType.TEF,
        analysis_actions: tp.Optional[tp.Iterable[actions.Step]] = None,
        use_feature_model: bool = True
    ) -> tp.MutableSequence[actions.Step]:

        analysis_actions = [
            TraceFeaturePerfWithTime(project, self.get_handle(), True)
        ]
        return super().actions_for_project(
            project, instrumentation, analysis_actions, use_feature_model
        )

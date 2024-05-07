import typing as tp
from pathlib import Path

from benchbuild.command import ProjectCommand, cleanup
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from perfetto.trace_processor import TraceProcessor
from plumbum import local
from plumbum.cmd import llvm_xray

from varats.data.reports.compiled_binary_report import CompiledBinaryReport
from varats.experiment.experiment_util import (
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_default_compile_error_wrapped,
    ExperimentHandle,
    VersionExperiment,
)
from varats.experiment.wllvm import RunWLLVM
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.base.precompile import StoreBinaries, RestoreBinaries
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_precision import (
    select_project_binaries,
)
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.hot_functions_report import (
    HotFunctionReport,
    WLHotFunctionAggregate,
)
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


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

    wl_commands += workload_commands(project, binary, [WorkloadCategory.MEDIUM])

    return wl_commands


class RunXRayProfiler(actions.ProjectStep):
    """Profiling step that runs a XRay instrumented binary to extract function-
    level measurement data."""

    NAME = "RunInstrumentedXRayBinaries"
    DESCRIPTION = "Profile a project that was instrumented \
        with xray instrumentations."

    project: VProject

    def __init__(
        self, project: VProject, experiment_handle: ExperimentHandle
    ) -> None:
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.run_instrumented_code()

    def __str__(self, indent: int = 0) -> str:
        return actions.textwrap.indent(
            f"* {self.project.name}: Run VaRA measurements together with XRay",
            indent * " "
        )

    def run_instrumented_code(self) -> actions.StepResult:
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                # Skip libraries as we cannot run them
                continue

            with local.cwd(local.path(self.project.builddir)):

                result_filepath = create_new_success_result_filepath(
                    exp_handle=self.__experiment_handle,
                    report_type=self.__experiment_handle.report_spec().
                    main_report,
                    project=self.project,
                    binary=binary,
                    config_id=get_current_config_id(self.project)
                )
                with ZippedReportFolder(
                    result_filepath.full_path()
                ) as reps_tmp_dir:
                    for rep in range(0, 1):
                        for prj_command in perf_prec_workload_commands(
                            project=self.project, binary=binary
                        ):
                            hot_function_report_file = Path(reps_tmp_dir) / (
                                "hot-func-trace_"
                                f"{prj_command.command.label}_{rep}"
                                ".csv"
                            )

                            unique_tracefile_tag = \
                                f"xray_{prj_command.command.label}_{rep}."
                            with local.env(
                                XRAY_OPTIONS=" ".join([
                                    "patch_premain=true",
                                    "xray_mode=xray-basic",
                                    f"xray_logfile_base={unique_tracefile_tag}"
                                ])
                            ):
                                with cleanup(prj_command):
                                    pb_cmd = prj_command.command.as_plumbum(
                                        project=self.project
                                    )
                                    pb_cmd(retcode=binary.valid_exit_codes)

                            for f in Path(".").iterdir():
                                if f.name.startswith(unique_tracefile_tag):
                                    xray_log_path = f.absolute()
                                    break

                            instr_map_path = local.path(
                                self.project.primary_source
                            ) / binary.path

                            # convert to trace event format
                            tef_file = f"tef_{prj_command.command.label}_{rep}"
                            llvm_xray(
                                "convert", "--symbolize", "--no-demangle",
                                f"--instr_map={instr_map_path}",
                                f"--output={tef_file}",
                                "--output-format=trace_event",
                                f"{xray_log_path}"
                            )

                            # reconstruct self-time from trace
                            trace = TraceProcessor(trace=tef_file)
                            result = trace.query(
                                f"""
INCLUDE PERFETTO MODULE time.conversion;

DROP VIEW IF EXISTS child_times;
CREATE PERFETTO VIEW child_times(id INT, dur INT) as
SELECT parent_id as id, SUM(dur) as dur FROM slice
GROUP BY parent_id;

SELECT
    slice.id as funcid,
    COUNT(slice.id) as count,
    MIN(slice.dur) as min,
    MAX(slice.dur) as max,
    SUM(slice.dur) as sum,
    SUM(slice.dur - IFNULL(child_times.dur, 0)) as self,
    slice.name as function
FROM slice
LEFT JOIN child_times
ON slice.id = child_times.id
GROUP BY name
ORDER BY funcid
LIMIT {HotFunctionReport.MAX_TRACK_FUNCTIONS};
                                """
                            ).as_pandas_dataframe()
                            result.to_csv(hot_function_report_file, index=False)

        return actions.StepResult.OK


class XRayFindHotFunctions(FeatureExperiment, shorthand="HF"):
    """Experiment for finding hot functions in code."""

    NAME = "DetermineHotFunctions"
    REPORT_SPEC = ReportSpecification(WLHotFunctionAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        return [
            RestoreBinaries(project, PreCompileXRayFindHotFunctions),
            RunXRayProfiler(project, self.get_handle()),
            actions.Clean(project),
        ]


class PreCompileXRayFindHotFunctions(VersionExperiment, shorthand="PRECHF"):
    """Stores binaries compiled for hot function detection as reports."""

    NAME = "PreCompileDetermineHotFunctions"

    REPORT_SPEC = ReportSpecification(CompiledBinaryReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        project.cflags += [
            "-fxray-instrument",
            "-fxray-instruction-threshold=1",
        ]

        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()

        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project,
            self.get_handle().report_spec().main_report
        )

        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        analysis_actions = [
            actions.Compile(project),
            StoreBinaries(project, self.get_handle()),
            actions.Clean(project)
        ]

        return analysis_actions

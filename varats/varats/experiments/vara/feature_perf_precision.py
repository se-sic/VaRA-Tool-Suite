"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import math
import tempfile
import textwrap
import typing as tp
from abc import abstractmethod
from collections import defaultdict
from itertools import chain, combinations
from pathlib import Path
from time import sleep

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult, Clean
from benchbuild.utils.cmd import time, rm, cp, numactl, sudo, bpftrace, perf
from data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from paper.paper_config import get_paper_config
from paper_mgmt.case_study import get_case_study_file_name_filter
from plumbum import local, BG
from plumbum.commands.modifiers import Future
from revision.revisions import get_processed_revisions_files

from varats.base.configuration import PatchConfiguration
from varats.containers.containers import get_base_image, ImageBase
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
from varats.projects.cpp_projects.dune import DunePerfRegression
from varats.projects.cpp_projects.hyteg import HyTeg
from varats.provider.patch.patch_provider import PatchProvider, PatchSet
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReportAggregate
from varats.tools.research_tools.vara import VaRA
from varats.utils.config import get_current_config_id, get_config
from varats.utils.git_util import ShortCommitHash

REPS = 3

IDENTIFIER_PATCH_TAG = 'perf_prec'


def default_patch_selector(project):
    patch_provider = PatchProvider.get_provider_for_project(project)
    patches = patch_provider.get_patches_for_revision(
        ShortCommitHash(project.version_of_primary)
    )[IDENTIFIER_PATCH_TAG]

    return [(p.shortname, [p]) for p in patches]


def RQ1_patch_selector(project):
    rq1_tags = get_tags_RQ1(project)

    patch_provider = PatchProvider.get_provider_for_project(project)

    patches = PatchSet(set())

    for tag in rq1_tags:
        patches |= patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )[tag, "regression"]

    return [(p.shortname, [p]) for p in patches]


def RQ2_patch_selector(project: VProject):
    paper_config = get_paper_config()
    case_studies = paper_config.get_case_studies(cs_name=project.name)
    current_config = get_current_config_id(project)

    report_files = get_processed_revisions_files(
        project.name,
        TEFFeatureIdentifier,
        TEFFeatureIdentifierReport,
        get_case_study_file_name_filter(case_studies[0]),
        config_id=current_config
    )

    if len(report_files) != 1:
        print("Invalid number of reports from TEFIdentifier")

    report_file = TEFFeatureIdentifierReport(report_files[0].full_path())

    if len(report_file.patches_containing_region("__VARA__DETECT__")) <= 5:
        patch_lists = build_patch_sets_under_5(report_file)
    else:
        patch_lists = build_patch_sets_over_5(report_files)

    ...


def build_patch_sets_under_5(report_file: TEFFeatureIdentifierReport):
    regressing_patches = {
        p[0]
        for p in report_file.patches_containing_region("__VARA__DETECT__")
        if len(p[1]) >= 2
    }
    patch_names = regressing_patches

    for patch in report_file.patch_names:
        if len(patch_names) >= 5:
            break

        if patch in patch_names:
            continue

        if any([
            "__VARA__DETECT__" in regions
            for regions in report_file.regions_for_patch(patch)
        ]):
            continue

        patch_names.add(patch)

    patch_lists = [
        set(s) for s in chain.from_iterable(
            combinations(patch_names, r)
            for r in range(1,
                           len(patch_names) + 1)
        )
    ]

    patch_lists = [s for s in patch_lists if regressing_patches.issubset(s)]

    return patch_lists


def build_patch_sets_over_5(report_file: TEFFeatureIdentifierReport):
    patch_candidates = defaultdict(str)
    region_candidates = defaultdict(lambda: math.inf)

    for region in report_file.affectable_regions:
        # We only consider regions that affect one other feature
        if len(region) != 2 or "__VARA__DETECT__" not in region:
            continue

        # Check all patches that affect exactly this region
        for patch in report_file.patches_for_regions(region):
            patch_name = patch[0]

            consider_patch = False
            num_affections = math.inf
            for patch_region in report_file.regions_for_patch(patch_name):
                # We do not care about unaffected regions
                if "__VARA__DETECT__" not in patch_region[0]:
                    continue

                # This is our region of interest
                if patch_region[0] == region:
                    consider_patch = True
                    num_affections = patch_region[1]
                    continue

                # At this point, we know that we don't want to consider the patch
                # It has the __VARA__DETECT__ interaction but is not our region of interest
                # That means that either also other regions are affected by this patch
                consider_patch = False
                break

            if consider_patch:
                if region_candidates[patch_name] < num_affections:
                    patch_candidates[region] = patch_name

    region_candidates = sorted(region_candidates, key=lambda kv: kv[1])[:4]

    patch_candidates = {r: patch_candidates[r] for r, _ in region_candidates}

    # patch_candidates now has a maximum of 4 entries
    patch_names = patch_candidates.values()
    # Build the powerset
    patch_lists = chain.from_iterable(
        combinations(patch_names, r) for r in range(1,
                                                    len(patch_names) + 1)
    )

    # 2nd step of patch selection:


def get_feature_tags(project):
    config = get_config(project, PatchConfiguration)
    if not config:
        return []

    result = {opt.value for opt in config.options()}

    return result


def get_tags_RQ1(project):
    result = get_feature_tags(project)

    to_remove = [
        "SynthCTCRTP", "SynthCTPolicies", "SynthCTTraitBased",
        "SynthCTTemplateSpecialization"
    ]

    for s in to_remove:
        if s in result:
            result.remove(s)

    return result


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
        f_tags = get_feature_tags(project)

        grid_binary_map = {
            "YaspGrid": "poisson_yasp_q2_3d",
            "UGGrid": "poisson_ug_pk_2d",
            "ALUGrid": "poisson_alugrid"
        }

        for grid in grid_binary_map:
            if grid in f_tags:
                return [
                    binary for binary in project.binaries
                    if binary.name == grid_binary_map[grid]
                ]

    return [project.binaries[0]]


def get_extra_cflags(project: VProject) -> tp.List[str]:
    if project.name in ["DunePerfRegression", "HyTeg"]:
        # Disable phasar for dune as the analysis cannot handle dunes size
        return ["-fvara-disable-phasar"]

    return []


def get_threshold(project: VProject) -> int:
    if project.DOMAIN is ProjectDomains.TEST:
        if project.name in [
            "SynthSAFieldSensitivity", "SynthIPRuntime", "SynthIPTemplate",
            "SynthIPTemplate2", "SynthIPCombined"
        ]:
            print("Don't instrument everything")
            return 10

        return 0

    if project.DOMAIN is ProjectDomains.HPC:
        return 0

    return 100


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

                                pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                                    adapted_binary_location=
                                    adapted_binary_location,
                                    project=self.project
                                )

                                bpf_runner = bpf_runner = self.attach_usdt_raw_tracing(
                                    local_tracefile_path,
                                    adapted_binary_location,
                                    Path(non_nfs_tmp_dir)
                                )

                                with cleanup(prj_command):
                                    print(
                                        f"Running example {prj_command.command.label}"
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
        # bpftrace_cmd = numactl["--cpunodebind=0", "--membind=0", bpftrace_cmd]

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

                            bpf_runner = bpf_runner = self.attach_usdt_bcc(
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
        # bcc_cmd = numactl["--cpunodebind=0", "--membind=0", bcc_cmd]

        bcc_runner = bcc_cmd & BG
        sleep(3)  # give bcc script time to start up
        return bcc_runner


def setup_actions_for_vara_experiment(
    experiment: FeatureExperiment,
    project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBase],
    patch_selector=RQ1_patch_selector
) -> tp.MutableSequence[actions.Step]:
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

    patchlists = patch_selector(project)
    print(f"{patchlists=}")

    patch_steps = []
    for name, patches in patchlists:
        for patch in patches:
            print(f"Got patch with path: {patch.path}")
            patch_steps.append(ApplyPatch(project, patch))
        patch_steps.append(ReCompile(project))
        patch_steps.append(
            analysis_step(
                project,
                binary,
                file_name=MultiPatchReport.
                create_custom_named_patched_report_name(
                    name, "rep_measurements"
                )
            )
        )
        for patch in reversed(patches):
            patch_steps.append(RevertPatch(project, patch))

    analysis_actions = get_config_patch_steps(project)

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
            self, project, FeatureInstrType.USDT_RAW, RunBPFTracedWorkloads
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
            self, project, FeatureInstrType.USDT, RunBCCTracedWorkloads
        )


class RunBlackBoxBaseline(OutputFolderStep):  # type: ignore
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
                    for prj_command in perf_prec_workload_commands(
                        self.project, self.__binary
                    ):
                        time_report_file = Path(reps_tmp_dir) / (
                            f"baseline_{prj_command.command.label}_{rep}"
                            f".{self.__report_file_ending}"
                        )

                        print(f"Running example {prj_command.command.label}")

                        with cleanup(prj_command):
                            pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                                time["-v", "-o", time_report_file],
                                project=self.project
                            )
                            pb_cmd(retcode=self.__binary.valid_exit_codes)

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

        project.cflags += get_extra_cflags(project)

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

        # TODO: change to multiple binaries
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        patchlists = RQ1_patch_selector(project)

        patch_steps = []
        for name, patches in patchlists:
            for patch in patches:
                print(f"Got patch with path: {patch.path}")
                patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                RunBlackBoxBaseline(
                    project,
                    binary,
                    file_name=MPRTimeReportAggregate.
                    create_custom_named_patched_report_name(
                        name, "rep_measurements"
                    )
                )
            )
            for patch in reversed(patches):
                patch_steps.append(RevertPatch(project, patch))

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    RunBlackBoxBaseline(
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
                            pb_cmd = prj_command.command.as_plumbum_wrapped_with(
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

                            pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                                time["-v", "-o", time_report_file],
                                adapted_binary_location,
                                project=self.project
                            )

                            bpf_runner = RunBPFTracedWorkloads.attach_usdt_raw_tracing(
                                fake_tracefile_path, adapted_binary_location,
                                Path(non_nfs_tmp_dir)
                            )

                            with cleanup(prj_command):
                                print(
                                    f"Running example {prj_command.command.label}"
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
                for prj_command in perf_prec_workload_commands(
                    self.project, self.__binary
                ):
                    time_report_file = tmp_dir / (
                        f"overhead_{prj_command.command.label}_{rep}"
                        f".{self.__report_file_ending}"
                    )

                    with cleanup(prj_command):
                        print(f"Running example {prj_command.command.label}")
                        pb_cmd = prj_command.command.as_plumbum_wrapped_with(
                            time["-v", "-o", time_report_file],
                            project=self.project
                        )

                        pb_cmd(retcode=self.__binary.valid_exit_codes)

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

        project.cflags += get_extra_cflags(project)

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

        # TODO: change to multiple binaries
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        analysis_actions = get_config_patch_steps(project)

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

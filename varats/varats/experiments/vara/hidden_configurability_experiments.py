import pprint
import re
import textwrap
import typing as tp
from collections import defaultdict
from pathlib import Path

import benchbuild as bb
import benchbuild.extensions as bb_ext
import yaml
from benchbuild import Project
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult, Echo, Step
from benchbuild.utils.cmd import git
from plotly.data import experiment
from plumbum import local, ProcessExecutionError

from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
    MPRTimeWLAggregate,
)
from varats.data.reports.llvm_cov_report import LLVMCoverageReport
from varats.data.reports.text_report import PlainTextReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    create_new_success_result_filepath,
    WithUnlimitedStackSize,
    get_default_compile_error_wrapped,
    get_config_patch_steps,
    ZippedExperimentSteps,
    ZippedReportFolder,
    get_config_reverse_patch_steps,
)
from varats.experiment.steps.combinators import OutputAdapter, AlwaysOk
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.steps.testsuite import (
    RunTestSuite,
    PrepareTestSuite,
    BuildTestSuite,
)
from varats.experiment.workload_util import (
    workload_commands,
    create_workload_specific_filename,
    WorkloadCategory,
)
from varats.experiments.coverage.collect_coverages import CollectBinaryCoverages
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_precision import (
    AnalysisProjectStepBase,
)
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.project.varats_project import VProject, SupportsTestSuites
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.revision.revisions import get_processed_revisions_files
from varats.tools.research_tools.vara import VaRA
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ChurnConfig, ShortCommitHash

NUM_REPETITIONS = 10


class HiddenConfigurabilityDetector(actions.ProjectStep):  #type: ignore
    """Detects hidden configurability points in the project."""

    NAME = "HiddenConfigurabilityDetector"

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Find Hidden Configuration Points",
            " " * indent
        )

    def analyze(self) -> actions.StepResult:
        """This step detects hidden configurability points in the project."""
        print("Running HiddenConfigurabilityDetector")

        binary = self.project.binaries[0]

        result_file = create_new_success_result_filepath(
            self.__experiment_handle, HiddenConfigurabilityReport, self.project,
            binary
        )

        project_directory = self.project.source_of_primary

        # Create a list of all C/CPP files in the project
        files = []

        churn_config = ChurnConfig.create_c_style_languages_config()
        file_pattern = re.compile(
            "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
        )

        with local.cwd(project_directory):
            files = [
                file for file in git(
                    "ls-tree",
                    "-r",
                    "--name-only",
                    "HEAD",
                ).splitlines() if file_pattern.match(file)
            ]

            submodule_files = [
                line for line in git(
                    "submodule",
                    "foreach",
                    "--recursive",
                    "git ls-tree -r --name-only HEAD",
                ).splitlines()
            ]

            sm_path = ""
            for line in submodule_files:
                if line.startswith("Entering"):
                    sm_path = line.split(" ")[1].strip("' ")

                if not file_pattern.match(line):
                    continue

                files.append(sm_path + "/" + line)

        # Run the HiddenConfigurabilityDetector
        hvf = local[VaRA.install_location() / "bin" /
                    "hidden-variability-finder"]

        with local.cwd(project_directory):
            run_cmd = hvf[f"--report-file={result_file}",
                          f"--root-dir={project_directory}"]
            run_cmd = run_cmd[files]

            bb.watch(run_cmd)()

        return actions.StepResult.OK


class FilterHiddenConfigurabilityPoints(actions.ProjectStep):  #type: ignore
    """Filters hidden configurability points from the report."""

    NAME = "FilterHiddenConfigurabilityPoints"

    project: VProject

    __GLOBAL_IGNORED_PATTERNS = [
        "/usr/include",
        "test",
        "examples",
    ]

    __PROJECT_SPECIFIC_IGNORED_PATTERNS = {"HyTeg": ["eigen/"]}

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.filter()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Filter Hidden Configuration Points",
            " " * indent
        )

    def __filter_ignored_patterns(self, report_data: dict) -> dict:
        ignored_patterns = self.__GLOBAL_IGNORED_PATTERNS

        if self.project.name in self.__PROJECT_SPECIFIC_IGNORED_PATTERNS:
            ignored_patterns.extend(
                self.__PROJECT_SPECIFIC_IGNORED_PATTERNS[self.project.name]
            )

        ignored_patterns = re.compile(
            "|".join(re.escape(pattern) for pattern in ignored_patterns)
        )

        for _, points in report_data.items():
            for point in points:
                print(point["Location"]["Filename"])
                if ignored_patterns.search(point["Location"]["Filename"]):
                    print("Filename matched ignored pattern")
                    point["tags"] = getattr(point, "tags",
                                            []) + ["Excluded (Filename)"]

        return report_data

    def __filter_coverage_based(self, report_data: dict) -> dict:
        # Filter points that are not covered according to coverage report
        coverage_reports = get_processed_revisions_files(
            self.project.name,
            CollectBinaryCoverages,
            LLVMCoverageReport,
            config_id=get_current_config_id(self.project)
        )

        if not coverage_reports or len(coverage_reports) > 1:
            print(
                f"Expected exactly one coverage report for {self.project.name}, found {len(coverage_reports)}"
            )
            return report_data

        coverage_report = LLVMCoverageReport(coverage_reports[0].full_path())
        pprint.pprint(report_data)
        for _, points in report_data.items():
            for point in points:
                # For each point create a map from files to lines they are used at
                use_locations = defaultdict(list)

                # First, the location of the definition
                use_locations[point["Location"]["Filename"]].append(
                    point["Location"]["Lineno"]
                )

                # Then all use locations
                for use in point["UseLocations"]:
                    use_locations[use["Filename"]].append(use["Lineno"])

                # Check if any of the locations is covered
                if not any(
                    coverage_report.is_covered(file, line)
                    for file, lines in use_locations.items()
                    for line in lines
                ):
                    if "tags" in point:
                        point["tags"].extend(["Excluded (Coverage)"])
                    else:
                        point["tags"] = ["Excluded (Coverage)"]

        #pprint.pprint(report_data)
        return report_data

    def filter(self) -> actions.StepResult:
        # Load the report
        reports = get_processed_revisions_files(
            self.project.name, FindHiddenConfigurationPoints,
            HiddenConfigurabilityReport
        )

        if not reports:
            return actions.StepResult.ERROR

        if len(reports) > 1:
            print(f"More than one report for {self.project.name}")
            return actions.StepResult.ERROR

        # TODO: Handle multiple reports? (Should not happen currently)

        # We do not load the actual report, but rather directly load it as a dict
        # and then filter it, as we do not have bindings for the data types
        # in the report generated from LLVM.

        with open(reports[0].full_path(), "r") as f:
            report_data = yaml.safe_load(f)

        report_data = self.__filter_ignored_patterns(report_data)

        report_data = self.__filter_coverage_based(report_data)

        result_filename = create_new_success_result_filepath(
            self.__experiment_handle, HiddenConfigurabilityReport, self.project,
            self.project.binaries[0]
        )

        with open(result_filename.full_path(), "w") as f:
            yaml.dump(report_data, f)

        return actions.StepResult.OK


class FindHiddenConfigurationPoints(VersionExperiment, shorthand="HCP"):
    """Detects hidden configurability points in the project."""

    NAME = "FindHiddenConfigurationPoints"
    REPORT_SPEC = ReportSpecification(HiddenConfigurabilityReport)

    def actions_for_project(self, project: VProject) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
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

        # Wrap compile action such that we can continue, even if it fails.
        # While it helps us to have a compile_commands.json, some projects might
        # not compile but the HiddenConfigurabilityDetector might still work to a certain extent.
        experiment_steps = [
            actions.Any([
                actions.Compile(project),
                HiddenConfigurabilityDetector(project, self.get_handle()),
                actions.Clean(project)
            ])
        ]

        return experiment_steps


class FilterHiddenConfigurabilityReport(VersionExperiment, shorthand="FCP"):

    NAME = "FilterHiddenConfigurabilityReport"
    REPORT_SPEC = ReportSpecification(HiddenConfigurabilityReport)

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        # Check whether the project already has a hidden configurability report
        # Load the report
        reports = get_processed_revisions_files(
            project.name, FindHiddenConfigurationPoints,
            HiddenConfigurabilityReport
        )

        if not reports:
            experiment_steps = [
                Echo(
                    f"No HiddenConfigurabilityReport found for {project.name}, skipping filtering."
                )
            ]
        else:
            experiment_steps = [
                FilterHiddenConfigurabilityPoints(project, self.get_handle())
            ]

        return experiment_steps


# Mapping of patches per project to possible variations
# for patch rendering.
PATCH_VARIATIONS = {
    "libzmq": {
        "hwm_template":
            ("hwm", [x for x in range(100, 2000, 100) if x != 1000]),
    },
    "brotli": {
        "command_block_cost": (
            "command_block_cost",
            [x / 10 for x in range(120, 150, 1) if x != 135]
        ),
        "literal_block_cost": (
            "literal_block_cost",
            [x / 10 for x in range(270, 300, 1) if x != 281]
        ),
        "distance_block_cost": (
            "distance_block_cost",
            [x / 10 for x in range(130, 160, 1) if x != 146]
        ),
        "min_entropy":
            ("min_entropy", [x / 100 for x in range(650, 950, 10) if x != 792]),
        "min_utf_ratio":
            ("min_utf_ratio", [x / 100 for x in range(50, 100, 5) if x != 75]),
        "sample_rate": (
            "sample_rate", [x for x in range(10, 20) if x != 13] +
            [13 * i for i in range(2, 6)]
        ),
    },
    "DunePerfRegression": {
        "hexa_gitter_refinement": (
            "resolution",
            [x for x in range(25, 100, 25)] + [x for x in range(100, 500, 50)]
        ),
        "alu_repartition": ("mem_factor", [x for x in range(3, 10, 1)]),
    },
    "FastDownward": {
        "extra_columns": ("extra_columns", [x for x in range(1, 10)]),
        "max_distance":
            ("max_distance", [2**x for x in range(1, 10) if 2**x != 32]),
        "memory_padding": (
            "memory_padding_mb",
            [25] + [x for x in range(50, 105, 5) if x != 75] + [150, 225, 300]
        ),
        "preconditions_to_test":
            ("preconditions_to_test", [x for x in range(2, 11) if x != 5]),
    },
    "libvpx": {
        "block_size_vp9_enc":
            ("block_size", [2**x for x in range(1, 7) if x != 4]),
        "cq_adjust_one_pass": ("cq_adjust", [0.05, 0.2, 0.4, 0.6, 0.8]),
        "cq_adjust_two_pass": ("cq_adjust", [0.05, 0.2, 0.4, 0.6, 0.8]),
        "kMaxMfBoost":
            ("kMaxMfBoost", [250, 500, 1000, 1500, 3000, 4000, 10000]),
        "min_filter_pick":
            ("min_filter_level", [1, 2, 3, 4] + [x for x in range(5, 20, 2)]),
        "min_filter_search":
            ("min_filter_level", [1, 2, 3, 4] + [x for x in range(5, 20, 2)]),
        "mv_threshold": ("mv_threshold", [25, 50, 150, 200, 400, 800, 1000]),
        "pred_stride": ("pred_stride", [4, 8, 16, 32, 128]),
        "pred_stride_rd": ("pred_stride", [4, 8, 16, 32, 128])
    },
}

_PROJECT_WORKLOADS = {
    "DunePerfRegression": [
        "poisson-yasp-q2-3d", "poisson-alugrid", "poisson-non-separated"
    ],
    "FastDownward": ["data-network-opt18-py", "sokoban-sat08-py"],
    "libvpx": ["nocturne-1080p"],
    "libzmq": ["bench-inproc-lat", "bench-inproc-thr", "bench-radix-tree"],
    "brotli": ["geo-maps-countries-land-1km", "geo-maps-countries-land-2km5"]
}


def variation_value_to_str(value: tp.Any) -> str:
    return str(value).replace('.', '')


def _filter_workloads(project: VProject,
                      binary: ProjectBinaryWrapper) -> tp.List[ProjectCommand]:
    return [
        cmd for cmd in workload_commands(project, binary, [])
        if cmd.command.label in _PROJECT_WORKLOADS[project.name]
    ]


class TimePatchedWorkloadsStep(AnalysisProjectStepBase):
    NAME = "TimePatchedWorkloads"
    DESCRIPTION = "Time patched workloads."

    project: VProject

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        return self.time_workloads(tmp_dir)

    def time_workloads(self, tmp_dir: Path) -> StepResult:
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / self._file_name
            with ZippedReportFolder(zip_tmp_dir) as reps_tmp_dir:
                for rep in range(0, self._reps):
                    for prj_command in _filter_workloads(
                        self.project, self._binary
                    ):
                        print(f"Running {prj_command.command.label}...")
                        time_report_file = reps_tmp_dir / create_workload_specific_filename(
                            "time_report", prj_command.command, rep, ".txt"
                        )

                        pb_cmd = prj_command.command.as_plumbum(
                            project=self.project
                        )
                        run_cmd = local["time"]["-v", "-o",
                                                f"{time_report_file}",
                                                pb_cmd.formulate()]

                        with cleanup(prj_command):
                            bb.watch(run_cmd)()

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Time patched workloads for binary {self._binary.name}",
            " " * indent
        )


def _get_project_binaries(project):
    if project.name == "FastDownward":
        return [
            binary for binary in project.binaries if binary.name == "FDDriverPy"
        ]

    return project.binaries


class TimePatchedWorkloads(FeatureExperiment, shorthand="TPWL"):
    """Generates time report files for patched workloads."""

    NAME = "TimePatchedWorkloads"
    REPORT_SPEC = ReportSpecification(MPRTimeWLAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(project, self) \
                                     << bb_ext.run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )["hidden-config"]

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))

        for binary in _get_project_binaries(project):
            if len(
                workload_commands(
                    project, binary, [
                        WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL,
                        WorkloadCategory.MEDIUM
                    ]
                )
            ) == 0:
                analysis_actions.append(
                    Echo(
                        f"Skipping binary {binary.name} as it has no workloads."
                    )
                )
                continue

            result_filepath = create_new_success_result_filepath(
                self.get_handle(), self.REPORT_SPEC.main_report, project,
                binary, get_current_config_id(project)
            )

            if not isinstance(analysis_actions[-1], actions.Compile):
                analysis_actions.append(ReCompile(project))

            patch_steps = []

            for patch in patches:
                # Skip patches without any variations
                if patch.shortname not in PATCH_VARIATIONS[project.name]:
                    print(
                        f"Skipping patch {patch.shortname} for project "
                        f"{project.name} as it has no variations."
                    )
                    continue

                arg_name, values = PATCH_VARIATIONS[project.name][
                    patch.shortname]

                for value in values:
                    patch_steps.append(
                        ApplyPatch(project, patch, **{arg_name: value})
                    )
                    patch_steps.append(ReCompile(project))
                    patch_steps.append(
                        AlwaysOk(
                            project,
                            TimePatchedWorkloadsStep(
                                project,
                                binary,
                                file_name=MPRTimeWLAggregate.
                                create_patched_report_name(
                                    patch, binary.name, **{arg_name: value}
                                ),
                                report_file_ending=".txt",
                                reps=NUM_REPETITIONS
                            )
                        )
                    )

                    patch_steps.append(
                        RevertPatch(project, patch, **{arg_name: value})
                    )

            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimePatchedWorkloadsStep(
                            project,
                            binary,
                            file_name=MPRTimeWLAggregate.
                            create_baseline_report_name(binary.name),
                            report_file_ending=".txt",
                            reps=NUM_REPETITIONS
                        )
                    ] + patch_steps
                )
            )

        analysis_actions.extend(get_config_reverse_patch_steps(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class MPTextReport(
    MultiPatchReport,
    shorthand="MP" + PlainTextReport.shorthand(),
    file_type="zip"
):
    """Aggregate for MultiPatchReports that contain WLTimeReports."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PlainTextReport)


class TestPatchVariations(FeatureExperiment, shorthand="TPV"):

    NAME = "TestPatchVariations"
    REPORT_SPEC = ReportSpecification(MPTextReport)

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(project, self) \
                                    << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(project, self) \
                                     << bb_ext.run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )["hidden-config"]

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(PrepareTestSuite(project))
        analysis_actions.append(BuildTestSuite(project))

        patch_steps = []
        fake_binary = ProjectBinaryWrapper(
            "TESTSUITE", Path(), BinaryType.EXECUTABLE
        )

        result_file = create_new_success_result_filepath(
            self.get_handle(), MPTextReport, project, fake_binary,
            get_current_config_id(project)
        )

        def adapt_test_step_output(test_step: RunTestSuite, tmp_dir: Path):
            test_step.set_output_path(tmp_dir / test_step.output_path.name)

        for patch in patches:
            # Skip patches without any variations
            if patch.shortname not in PATCH_VARIATIONS[project.name]:
                print(
                    f"Skipping patch {patch.shortname} for project "
                    f"{project.name} as it has no variations."
                )
                continue

            arg_name, values = PATCH_VARIATIONS[project.name][patch.shortname]

            for value in values:
                patch_steps.append(
                    ApplyPatch(project, patch, **{arg_name: value})
                )
                patch_steps.append(BuildTestSuite(project))
                patch_steps.append(
                    AlwaysOk(
                        project,
                        OutputAdapter(
                            project,
                            RunTestSuite(
                                project,
                                Path(
                                    MPTextReport.create_patched_report_name(
                                        patch, "testsuite", **{arg_name: value}
                                    )
                                )
                            ), adapt_test_step_output
                        )
                    )
                )

                patch_steps.append(
                    RevertPatch(project, patch, **{arg_name: value})
                )

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file, [
                    AlwaysOk(
                        project,
                        OutputAdapter(
                            project,
                            RunTestSuite(
                                project,
                                Path(
                                    MultiPatchReport.
                                    create_baseline_report_name("testsuite")
                                )
                            ), adapt_test_step_output
                        )
                    )
                ] + patch_steps
            )
        )

        analysis_actions.extend(get_config_reverse_patch_steps(project))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

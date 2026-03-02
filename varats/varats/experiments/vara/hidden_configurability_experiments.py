import re
import textwrap
import typing as tp
from collections import defaultdict
from pathlib import Path

import benchbuild as bb
import benchbuild.extensions as bb_ext
import yaml
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult, Echo, Step
from benchbuild.utils.cmd import git
from benchbuild.utils.settings import get_number_of_jobs
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
    WithEnvironment,
    create_stable_success_result_filepath,
)
from varats.experiment.steps.combinators import (
    OutputAdapter,
    AlwaysOk,
    IfThenElse,
)
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
from varats.experiments.hidden_config.benchbase_experiments import (
    BenchbaseCoverage,
)
from varats.experiments.hidden_config.database_utils import SupportsBenchbase
from varats.experiments.hidden_config.hidden_config_utils import (
    PATCH_VARIATIONS,
    get_variations,
    get_variations_as_dict,
    sample_variations,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_precision import (
    AnalysisProjectStepBase,
)
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.project.varats_project import VProject
from varats.projects.c_projects.brotli import Brotli
from varats.projects.c_projects.bzip2 import Bzip2
from varats.projects.c_projects.gzip import Gzip
from varats.projects.c_projects.lrzip import Lrzip
from varats.projects.c_projects.postgres import PostgreSQL
from varats.projects.c_projects.sqlite import SQLite
from varats.projects.c_projects.xz import Xz
from varats.projects.cpp_projects.duckdb import DuckDB
from varats.projects.cpp_projects.dune import DunePerfRegression
from varats.projects.cpp_projects.ect import Ect
from varats.projects.cpp_projects.fast_downward import FastDownward
from varats.projects.cpp_projects.hyteg import HyTeg
from varats.projects.cpp_projects.lepton import Lepton
from varats.projects.cpp_projects.mariadb import MariaDB
from varats.projects.cpp_projects.sevenZip import SevenZip
from varats.provider.patch.patch_provider import PatchProvider, Patch
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
        print(
            f"Running HiddenConfigurabilityDetector for {self.project.name}..."
        )
        binary = self.project.binaries[0]

        result_file = create_new_success_result_filepath(
            self.__experiment_handle, HiddenConfigurabilityReport, self.project,
            binary, get_current_config_id(self.project)
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

        print(
            f"Running HiddenConfigurabilityDetector for {len(files)} source code files..."
        )
        # Run the HiddenConfigurabilityDetector
        hvf = local[VaRA.install_location() / "bin" /
                    "hidden-variability-finder"]

        vara_lib_path = VaRA.install_location() / "lib"
        hvf = hvf.with_env(LD_LIBRARY_PATH=str(vara_lib_path))

        with local.cwd(project_directory):
            run_cmd = hvf[f"--report-file={result_file}",
                          f"--root-dir={project_directory}"]
            run_cmd = run_cmd[files]

            try:
                bb.watch(run_cmd)()
            except ProcessExecutionError as e:
                print(
                    f"Error while running HiddenConfigurabilityDetector for {self.project.name}: {e}"
                )

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

    __PROJECT_SPECIFIC_IGNORED_PATTERNS = {
        HyTeg.NAME: ["eigen/"],
        SevenZip.NAME: ["Windows/", "UI/"],
        Brotli.NAME: ["csharp/", "go/", "java/", "js/", "python/", "research/"],
        Xz.NAME: ["debug/", "doc/", "windows/"],
        Lepton.NAME: ["dependencies/", "test_suite/"],
        Ect.NAME: [
            "libpng/", "leanify/", "lodepng/", "miniz/", "mozijpeg/",
            "optipng/", "zlib/", "zopfli/"
        ],
        Lrzip.NAME: ["libzpaq/", "lzo/", "lzma/", "m4/"],
        Bzip2.NAME: [],
        Gzip.NAME: ["m4"],
        MariaDB.NAME: ["dbug/", "wsrep-lib/", "zlib/"],
        SQLite.NAME: [],
        PostgreSQL.NAME: [],
        DuckDB.NAME: ["benchmark/", "extensions/", "third_party/"],
        FastDownward.NAME: [],
        DunePerfRegression.NAME: ["dune-performance-regression/"],
    }

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
                #print(point["Location"]["Filename"])
                if ignored_patterns.search(point["Location"]["Filename"]):
                    #print("Filename matched ignored pattern")
                    point["tags"] = getattr(point, "tags",
                                            []) + ["Excluded (Filename)"]

        return report_data

    def __filter_coverage_based(self, report_data: dict) -> dict:
        # Filter points that are not covered according to coverage report
        if isinstance(self.project, SupportsBenchbase):
            exp_type = BenchbaseCoverage
        else:
            exp_type = CollectBinaryCoverages

        coverage_reports = get_processed_revisions_files(
            self.project.name,
            exp_type,
            LLVMCoverageReport,
            config_id=get_current_config_id(self.project)
        )

        if not coverage_reports or len(coverage_reports) > 1:
            print(
                f"Expected exactly one coverage report for {self.project.name}, found {len(coverage_reports)}"
            )
            return report_data

        try:
            coverage_report = LLVMCoverageReport(
                coverage_reports[0].full_path()
            )
        except:
            print(
                f"Failed to load coverage report for {self.project.name} from "
                f"{coverage_reports[0].full_path()}"
            )
            return report_data
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

    def __filter_literal_bin_operations(self, report_data: dict) -> dict:
        # Filter literal bin operations based on operand
        __LITERAL_BIN_OP_KEY = "LiteralComp"

        for point in report_data.get(__LITERAL_BIN_OP_KEY, []):
            if point["Operator"] not in [
                "==", "!=", "<", ">", "<=", ">=", "+=", "-=", "*=", "/="
            ]:
                point["tags"] = getattr(point, "tags",
                                        []) + ["Excluded (Operand)"]

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

        report_data = self.__filter_literal_bin_operations(report_data)

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
        ) << WithUnlimitedStackSize() << WithEnvironment({
            "CMAKE_EXPORT_COMPILE_COMMANDS": "1"
        })

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


_PROJECT_WORKLOADS = {
    "DunePerfRegression": [
        "poisson-yasp-q2-3d", "poisson-alugrid", "poisson-non-separated"
    ],
    "FastDownward": ["data-network-opt18-py", "sokoban-sat08-py"],
    "libvpx": ["nocturne-1080p"],
    "libzmq": ["bench-inproc-lat", "bench-inproc-thr", "bench-radix-tree"],
    "brotli": ["geo-maps-countries-land-1km", "geo-maps-countries-land-2km5"],
    "xz": ["countries-land-10m", "countries-land-250m"],
    "7zip": ["countries-10m-geo", "countries-100m-geo"],
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

                        run_cmd = prj_command.command.as_plumbum_wrapped_with(
                            local["time"]["-v", "-o", f"{time_report_file}"],
                            project=self.project
                        )

                        with cleanup(prj_command):
                            #bb.watch(run_cmd)()
                            run_cmd()

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

        variations = get_variations_as_dict(project)
        zipped_steps = []

        if len(variations) == 0:
            # Baseline step, test normal program behavior without any patch applied
            analysis_actions.append(actions.Compile(project))

            zipped_steps.extend([
                TimePatchedWorkloadsStep(
                    project,
                    binary,
                    file_name=MPRTimeWLAggregate.create_baseline_report_name(
                        binary.name
                    ),
                    report_file_ending=".txt",
                    reps=NUM_REPETITIONS
                ) for binary in _get_project_binaries(project)
            ])
        else:
            # Filter patches based on the variations specified in the configuration
            patches_filtered: tp.List[Patch] = [
                patch for patch in patches if patch.shortname in variations
            ]

            for patch in patches_filtered:
                patch_variations = variations[patch.shortname]

                if len(patch_variations) != 1:
                    print(
                        f"Warning: Patch '{patch.shortname}' defines more than one argument. This is not supported currently. Skipping this patch."
                    )
                    continue
                arg_name = next(iter(patch_variations))
                values: tp.List[int] = list(patch_variations[arg_name])

                if arg_name not in patch.arguments:
                    print(
                        f"Warning: Patch '{patch.shortname}' does not define argument '{arg_name}'."
                    )
                    print(f"Available arguments: {patch.arguments}")
                    continue

                num_samples = 20
                values.extend(sample_variations(values, num_samples))

                for value in values:
                    zipped_steps.append(
                        ApplyPatch(project, patch, **{arg_name: value})
                    )

                    if len(zipped_steps) == 1:
                        # First iteration, perform a full compile
                        zipped_steps.append(actions.Compile(project))
                    else:
                        zipped_steps.append(ReCompile(project))

                    zipped_steps.extend([
                        AlwaysOk(
                            TimePatchedWorkloadsStep(
                                project,
                                binary,
                                file_name=MPRTimeWLAggregate.
                                create_patched_report_name(
                                    patch, binary.name, **{
                                        arg_name: value
                                    }
                                ).replace('.', ''),
                                report_file_ending=".txt",
                                reps=NUM_REPETITIONS
                            )
                        ) for binary in _get_project_binaries(project)
                    ])

                    zipped_steps.append(
                        RevertPatch(project, patch, **{arg_name: value})
                    )

        fake_binary = ProjectBinaryWrapper("ALL", Path(), BinaryType.EXECUTABLE)
        result_filepath = create_stable_success_result_filepath(
            self.get_handle(), MPRTimeWLAggregate, project, fake_binary,
            get_current_config_id(project)
        )

        analysis_actions.append(
            ZippedExperimentSteps(result_filepath, zipped_steps)
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
        print(
            f"{patch_provider.get_patches_for_revision(ShortCommitHash(project.version_of_primary))=}"
        )
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )["hidden-config"]

        analysis_actions = get_config_patch_steps(project)

        fake_binary = ProjectBinaryWrapper(
            "TESTSUITE", Path(), BinaryType.EXECUTABLE
        )

        result_file = create_stable_success_result_filepath(
            self.get_handle(), MPTextReport, project, fake_binary,
            get_current_config_id(project)
        )

        variations = get_variations_as_dict(project)
        zipped_steps = []

        if len(variations) == 0:
            # Baseline step, test normal program behavior without any patch applied
            analysis_actions.append(AlwaysOk(PrepareTestSuite(project)))
            analysis_actions.append(BuildTestSuite(project))

            zipped_steps.append(
                AlwaysOk(
                    RunTestSuite(
                        project,
                        Path(
                            MultiPatchReport.
                            create_baseline_report_name("testsuite")
                        )
                    )
                )
            )
        else:
            # Filter patches based on the variations specified in the configuration
            patches_filtered: tp.List[Patch] = [
                patch for patch in patches if patch.shortname in variations
            ]

            # Test specific patch variations
            for patch in patches_filtered:
                patch_variations = variations[patch.shortname]

                if len(patch_variations) != 1:
                    print(
                        f"Warning: Patch '{patch.shortname}' defines more than one argument. This is not supported currently. Skipping this patch."
                    )
                    continue

                arg_name = next(iter(patch_variations))
                values: tp.List[int] = list(patch_variations[arg_name])

                if arg_name not in patch.arguments:
                    print(
                        f"Warning: Patch '{patch.shortname}' does not define argument '{arg_name}'."
                    )
                    print(f"Available arguments: {patch.arguments}")
                    continue

                # TODO: Change me
                num_samples = 20
                values.extend(sample_variations(values, num_samples))

                for value in values:
                    zipped_steps.append(
                        ApplyPatch(project, patch, **{arg_name: value})
                    )

                    if len(zipped_steps) == 1:
                        zipped_steps.append(AlwaysOk(PrepareTestSuite(project)))

                    zipped_steps.append(
                        IfThenElse(
                            project,
                            condition=BuildTestSuite(project),
                            then_step=AlwaysOk(
                                RunTestSuite(
                                    project,
                                    Path(
                                        MPTextReport.create_patched_report_name(
                                            patch, "testsuite",
                                            **{arg_name: value}
                                        )
                                    )
                                )
                            ),
                            return_result=StepResult.OK
                        )
                    )

                    zipped_steps.append(
                        RevertPatch(project, patch, **{arg_name: value})
                    )

        analysis_actions.append(
            ZippedExperimentSteps(result_file, zipped_steps)
        )

        analysis_actions.extend(get_config_reverse_patch_steps(project))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

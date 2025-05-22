import re
import textwrap
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult, Echo
from benchbuild.utils.cmd import git
from plumbum import local

from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
    MPRTimeWLAggregate,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    create_new_success_result_filepath,
    WithUnlimitedStackSize,
    get_default_compile_error_wrapped,
    get_config_patch_steps,
    ZippedExperimentSteps,
    ZippedReportFolder,
)
from varats.experiment.steps.combinators import IfThenElse
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.steps.testsuite import RunTestSuite
from varats.experiment.workload_util import (
    workload_commands,
    create_workload_specific_filename,
    WorkloadCategory,
)
from varats.experiments.base.just_test import PrintString
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.feature_perf_precision import (
    AnalysisProjectStepBase,
)
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
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

        print(f"Found {len(files)} files to analyze")
        print(files)

        print(f"{result_file=}")
        print(f"{project_directory=}")

        # Run the HiddenConfigurabilityDetector
        hvf = local[VaRA.install_location() / "bin" /
                    "hidden-variability-finder"]

        with local.cwd(project_directory):
            run_cmd = hvf[f"--report-file={result_file}",
                          f"--root-dir={project_directory}"]
            run_cmd = run_cmd[files]

            run_cmd()

        return actions.StepResult.OK


class FilterHiddenConfigurabilityPoints(actions.ProjectStep):  #type: ignore
    """Filters hidden configurability points from the report."""

    NAME = "FilterHiddenConfigurabilityPoints"

    project: VProject

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

    def filter(self) -> actions.StepResult:
        # Load the report
        reports = get_processed_revisions_files(
            self.project.name,
            FindHiddenConfigurationPoints,
            HiddenConfigurabilityReport,
            config_id=get_current_config_id(self.project)
        )

        if not reports:
            return actions.StepResult.ERROR

        if len(reports) > 1:
            print(f"More than one report for {self.project.name}")
            return actions.StepResult.ERROR

        report = HiddenConfigurabilityReport(reports[0].full_path())

        # General Filtering:
        # Ignore paths containing any of the following substrings:
        # - "/usr/include" - System Headers
        # - "test" - Test files
        # ... (May be extended)

        ignored_patterns = [
            "/usr/include",
            "test",
            "examples",
        ]

        if self.project.name == "HyTeg":
            ignored_patterns.append("eigen/")

        ignored_patterns = re.compile(
            "|".join(re.escape(pattern) for pattern in ignored_patterns)
        )

        report.__hidden_configurability_points = {
            kind: [
                point
                for point in points
                if not ignored_patterns.search(point.filename)
            ] for kind, points in
            report.get_hidden_configurability_points().items()
        }

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
        # not compile but the HiddenConfigurabilityDetector might still work.
        experiment_steps = [
            actions.Any([
                actions.Compile(project),
                HiddenConfigurabilityDetector(project, self.get_handle()),
                actions.Clean(project)
            ]),
            FilterHiddenConfigurabilityPoints(project, self.get_handle())
        ]

        return experiment_steps


# Mapping of patches per project to possible variations
# for patch rendering.
PATCH_VARIATIONS = {
    "libzmq": {
        "hwm_template": ("hwm", [x for x in range(100, 2000, 100)]),
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
    "FastDownward": {},
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


def variation_value_to_str(value: tp.Any) -> str:
    return str(value).replace('.', '')


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
                    for prj_command in workload_commands(
                        self.project, self._binary,
                        [WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL]
                    ):
                        time_report_file = reps_tmp_dir / create_workload_specific_filename(
                            "time_report", prj_command.command, rep, ".txt"
                        )

                        pb_cmd = prj_command.command.as_plumbum(
                            project=self.project
                        )
                        run_cmd = local["time"]["-v", "-o",
                                                f"{time_report_file}", pb_cmd]

                        with cleanup(prj_command):
                            run_cmd()

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Time patched workloads for binary {self._binary.name}",
            " " * indent
        )


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

        for binary in project.binaries:
            if len(
                workload_commands(
                    project, binary,
                    [WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL]
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
                        IfThenElse(
                            project,
                            PrintString(project, "Skipping test suite"),
                            TimePatchedWorkloadsStep(
                                project,
                                binary,
                                file_name=MPRTimeWLAggregate.
                                create_patched_report_name(patch, binary.name) +
                                f"_{arg_name.replace('_','-')}={variation_value_to_str(value)}",
                                report_file_ending=".txt",
                                reps=NUM_REPETITIONS
                            ),
                            PrintString(
                                project,
                                f"Testsuite failed for path {patch.shortname} with {arg_name}={value}"
                            ),
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

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

import shutil
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.actions import Step, Compile, ProjectStep, StepResult
from plumbum import local, ProcessExecutionError

from varats.data.reports.benchbase_report import BenchBaseReportAggregate
from varats.data.reports.llvm_cov_report import (
    LLVMCoverageReport,
    MWLCoverageReport,
)
from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    AsOutputFolderStep,
    ZippedExperimentSteps,
    get_config_patch_steps,
    get_config_reverse_patch_steps,
)
from varats.experiment.steps.combinators import AlwaysOk
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiments.coverage.collect_coverages import (
    CollectCoverage,
    MergeCoverages,
    BuildWithCoverage,
)
from varats.experiments.hidden_config.database_utils import SupportsBenchbase
from varats.experiments.hidden_config.hidden_config_utils import (
    PATCH_VARIATIONS,
    get_variations,
    HIDDEN_CONFIG_REPS,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash

_WORKLOADS = [
    "tpcc",
    "tpch",
    "auctionmark",
]


class BuildBenchbase(ProjectStep):
    """Builds the BenchBase benchmark suite."""

    def __init__(self, project: tp.Union[VProject, SupportsBenchbase]):
        super().__init__(project)

    def __call__(self) -> tp.Any:
        if not isinstance(self.project, SupportsBenchbase):
            print(f"Project '{self.project.name}' does not support benchbase.")
            self.status = StepResult.ERROR
            return self.status

        self.project: tp.Union[VProject, SupportsBenchbase]

        benchbase_repo_url = "https://github.com/cmu-db/benchbase.git"
        git = local["git"]

        with local.cwd(self.project.builddir):
            try:
                if not Path("benchbase").exists():
                    git("clone", "--depth", 1, benchbase_repo_url)
            except ProcessExecutionError as e:
                print(f"Error cloning BenchBase repository: {e}")
                self.status = StepResult.ERROR
                return self.status

            with local.cwd("benchbase"):
                mvnw = local["mvnw"]
                try:
                    mvnw(
                        "clean", "package", "-P",
                        self.project.get_benchbase_profile_name()
                    )
                except ProcessExecutionError as e:
                    print(f"Error building BenchBase: {e}")

                with local.cwd("target"):
                    benchbase_archive = f"benchbase-{self.project.get_benchbase_profile_name()}.tgz"
                    try:
                        local["tar"]["-xvzf", benchbase_archive]()
                    except ProcessExecutionError as e:
                        print(f"Error extracting BenchBase archive: {e}")
                        self.status = StepResult.ERROR
                        return self.status

        self.status = StepResult.OK
        return self.status

    def __str__(self, indent: int = 0) -> str:
        return " " * indent + f"* {self.project.name}: Build BenchBase"


def _run_benchbase(
    project: tp.Union[VProject, SupportsBenchbase], workload: str
) -> StepResult:
    benchbase_exec_dir = project.builddir / "benchbase" / "target" / f"benchbase-{project.get_benchbase_profile_name()}"

    with local.cwd(benchbase_exec_dir):
        print(f"Running workload: {workload}")
        # TODO: Customize configuration
        config = {}
        workload_config = project.render_workload_config(workload, config)

        run_cmd = local["java"]["-jar", "benchbase.jar", "-b", workload, "-c",
                                workload_config, "--create=true", "--load=true",
                                "--execute=true"]

        try:
            # Start the database server
            project.start_database_server()

            # Run the benchmark
            bb.watch(run_cmd)()
            status = StepResult.OK
        except ProcessExecutionError as e:
            print(f"Error running BenchBase workload '{workload}': {e}")
            status = StepResult.ERROR
        finally:
            # Stop the database server after benchmark
            project.stop_database_server()

        return status


@AsOutputFolderStep("result_file")
class RunBenchbase(ProjectStep):
    """Runs the BenchBase benchmark suite."""

    def __init__(
        self,
        project: tp.Union[VProject, SupportsBenchbase],
        result_file: Path,
        workload: str,
        reps: int = 1
    ):
        super().__init__(project)
        self.result_file = result_file
        self.__workload = workload
        self._reps = reps

    def __call__(self) -> tp.Any:
        if not isinstance(self.project, SupportsBenchbase):
            print(f"Project '{self.project.name}' does not support benchbase.")
            self.status = StepResult.ERROR
            return self.status

        self.project: tp.Union[VProject, SupportsBenchbase]

        benchbase_exec_dir = self.project.builddir / "benchbase" / "target" / f"benchbase-{self.project.get_benchbase_profile_name()}"

        for _ in range(self._reps):
            _run_benchbase(self.project, self.__workload)
        # Zip up results
        try:
            with local.cwd(benchbase_exec_dir / "results"):
                local["zip"]["-r", "-D", self.result_file.absolute(), "."]()
        except ProcessExecutionError as e:
            print(f"Error zipping results: {e}")
            self.status = StepResult.ERROR
            return self.status

        # Remove the results directory after zipping
        shutil.rmtree(benchbase_exec_dir / "results", ignore_errors=True)

        self.status = StepResult.OK
        return self.status

    def __str__(self, indent: int = 0) -> str:
        return " " * indent + f"* {self.project.name}: Run BenchBase (Workload: {self.__workload}; Reps: {self._reps})"


class BenchbaseBenchmark(FeatureExperiment, shorthand="BBB"):
    """Runs the BenchBase benchmark suite."""

    NAME = "RunBenchbase"
    DESCRIPTION = "Run the BenchBase benchmark suite"
    REPORT_SPEC = ReportSpecification(BenchBaseReportAggregate)

    _REPS = 3

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        if not isinstance(project, SupportsBenchbase):
            raise TypeError(
                f"Project {project.name} does not support benchbase."
            )

        project: tp.Union[VProject, SupportsBenchbase]

        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        db_binary = project.database_binary(
            ShortCommitHash(project.version_of_primary)
        )

        result_path = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project, db_binary,
            get_current_config_id(project)
        )

        analysis_actions: tp.List[Step] = [
            Compile(project),
            BuildBenchbase(project),
            ZippedExperimentSteps(
                result_path, [
                    RunBenchbase(project, Path(f"rep_{r}.zip"), wl)
                    for r in range(self._REPS)
                    for wl in _WORKLOADS
                ]
            )
        ]

        return analysis_actions


class MPBenchbaseReport(
    MultiPatchReport,
    shorthand="MP" + BenchBaseReportAggregate.SHORTHAND,
    file_type="zip"
):
    """Multi-patch report for BenchBase benchmark results."""

    def __init__(self, Path):
        super().__init__(Path, BenchBaseReportAggregate)


class BenchbaseHiddenConfig(FeatureExperiment, shorthand="BBHC"):
    """Runs the BenchBase benchmark suite with a hidden configuration."""

    NAME = "BenchbaseHiddenConfig"
    DESCRIPTION = "Run the BenchBase benchmark suite with a hidden configuration"
    REPORT_SPEC = ReportSpecification(
        MPBenchbaseReport
    )  # TODO: Proper MPReport for benchbase

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        if not isinstance(project, SupportsBenchbase):
            raise TypeError(
                f"Project {project.name} does not support benchbase."
            )

        project: tp.Union[VProject, SupportsBenchbase]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )["hidden-config"]

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(Compile(project))
        analysis_actions.append(BuildBenchbase(project))

        # TODO: Baseline measurements
        db_binary = project.database_binary(
            ShortCommitHash(project.version_of_primary)
        )

        baseline_steps = []
        baseline_steps.extend([
            RunBenchbase(
                project,
                Path(
                    MPBenchbaseReport.
                    create_baseline_report_name(f"{db_binary.name}-{wl}")
                ), wl, HIDDEN_CONFIG_REPS
            ) for wl in _WORKLOADS
        ])

        # TODO: Implement patch steps
        patch_steps = []

        for patch in patches:
            # Skip patches without variations
            if patch.shortname not in PATCH_VARIATIONS[project.name]:
                print(
                    f"Skipping patch {patch.shortname} as it has no variations."
                )
                continue

            arg_name, values = get_variations(project, patch.shortname)

            for value in values:
                patch_steps.append(
                    ApplyPatch(project, patch, **{arg_name: value})
                )
                patch_steps.append(ReCompile(project))
                patch_steps.extend([
                    AlwaysOk(
                        project,
                        RunBenchbase(
                            project,
                            Path(
                                MPBenchbaseReport.create_patched_report_name(
                                    patch, f"{db_binary.name}-{wl}",
                                    **{arg_name: value}
                                )
                            ), wl, HIDDEN_CONFIG_REPS
                        )
                    ) for wl in _WORKLOADS
                ])

                patch_steps.append(
                    RevertPatch(project, patch, **{arg_name: value})
                )

        result_filepath = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project, db_binary,
            get_current_config_id(project)
        )

        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, baseline_steps + patch_steps
            )
        )

        analysis_actions += get_config_reverse_patch_steps(project)

        return analysis_actions


class BenchbaseCoverage(FeatureExperiment, shorthand="BBC"):
    """Runs the BenchBase benchmark suite with coverage instrumentation."""

    NAME = "BenchbaseCoverage"
    DESCRIPTION = "Run the BenchBase benchmark suite with coverage instrumentation"
    REPORT_SPEC = ReportSpecification(LLVMCoverageReport, MWLCoverageReport)

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        if not isinstance(project, SupportsBenchbase):
            raise TypeError(
                f"Project {project.name} does not support benchbase."
            )

        project: tp.Union[VProject, SupportsBenchbase]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        project.cflags.extend([
            "-fprofile-instr-generate", "-fcoverage-mapping"
        ])

        db_binary = project.database_binary(
            ShortCommitHash(project.version_of_primary)
        )

        result_file = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project, db_binary,
            get_current_config_id(project)
        )

        steps: tp.MutableSequence[Step] = [
            BuildWithCoverage(project, project.compile),
            BuildBenchbase(project),
        ]

        prefixes = []
        zipped_steps = []

        bin_path = Path(project.source_of_primary) / db_binary.path

        for workload in _WORKLOADS:

            def bound_run():
                RunBenchbase._run_benchbase(project, workload)

            wl_result_file = f"{db_binary.name}_{workload}_0.zip"

            zipped_steps.extend([
                CollectCoverage(project, bound_run, workload),
                MergeCoverages(
                    project, bin_path.absolute(), f"{workload}", f"{workload}",
                    Path(wl_result_file)
                )
            ])

            prefixes.append(workload)

        agg_result_file = create_new_success_result_filepath(
            self.get_handle(), MWLCoverageReport, project, db_binary,
            get_current_config_id(project)
        )

        steps.append(ZippedExperimentSteps(agg_result_file, zipped_steps))

        steps.append(
            MergeCoverages(
                project, bin_path.absolute(), prefixes, "benchbase-cov",
                result_file.full_path().absolute()
            )
        )

        return steps

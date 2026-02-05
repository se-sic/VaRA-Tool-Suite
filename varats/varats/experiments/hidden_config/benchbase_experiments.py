import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.extensions import compiler, run
from benchbuild.utils.actions import Step, Compile, ProjectStep, StepResult
from plumbum import local, ProcessExecutionError

from varats.data.reports.benchbase_report import (
    BenchBaseReport,
    BenchBaseReportAggregate,
)
from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    AsOutputFolderStep,
    ZippedExperimentSteps,
)
from varats.experiment.workload_util import create_workload_specific_filename
from varats.experiments.hidden_config.database_utils import SupportsBenchbase
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.varats_project import VProject
from varats.projects.c_projects.postgres import PostgreSQL
from varats.projects.c_projects.sqlite import SQLite
from varats.projects.cpp_projects.mariadb import MariaDB
from varats.report.report import ReportFilepath, ReportSpecification
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash


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


@AsOutputFolderStep("result_file")
class RunBenchbase(ProjectStep):
    """Runs the BenchBase benchmark suite."""

    __DB_PROFILES = {
        MariaDB: "mariadb",
        PostgreSQL: "postgres",
        SQLite: "sqlite",
    }

    __WORKLOADS = [
        "tpcc",
        "tpch",
        "auctionmark",
    ]

    def __init__(
        self, project: tp.Union[VProject, SupportsBenchbase], result_file: Path
    ):
        super().__init__(project)
        self.result_file = result_file

    def __call__(self) -> tp.Any:
        if not isinstance(self.project, SupportsBenchbase):
            print(f"Project '{self.project.name}' does not support benchbase.")
            self.status = StepResult.ERROR
            return self.status

        self.project: tp.Union[VProject, SupportsBenchbase]

        benchbase_repo_url = "https://github.com/cmu-db/benchbase.git"
        git = local["git"]

        with local.cwd(self.project.builddir):
            with local.cwd(
                f"benchbase/target/benchbase-{self.project.get_benchbase_profile_name()}"
            ):
                for workload in self.__WORKLOADS:
                    print(f"Running workload: {workload}")
                    # TODO: Customize configuration
                    config = {}
                    workload_config = self.project.render_workload_config(
                        workload, config
                    )

                    run_cmd = local["java"]["-jar", "benchbase.jar", "-b",
                                            workload, "-c", workload_config,
                                            "--create=true", "--load=true",
                                            "--execute=true"]

                    try:
                        # Start the database server
                        self.project.start_database_server()

                        # Run the benchmark
                        bb.watch(run_cmd)()

                        # Stop the database server after benchmark
                        self.project.stop_database_server()
                    except ProcessExecutionError as e:
                        print(
                            f"Error running BenchBase workload '{workload}': {e}"
                        )
                        self.status = StepResult.ERROR
                        return self.status

                    # Zip up results
                    try:
                        with local.cwd("results"):
                            local["zip"]["-r", "-D",
                                         self.result_file.absolute(), "."]()
                    except ProcessExecutionError as e:
                        print(
                            f"Error zipping results for workload '{workload}': {e}"
                        )
                        self.status = StepResult.ERROR
                        return self.status

        self.status = StepResult.OK
        return self.status

    def __str__(self, indent: int = 0) -> str:
        return " " * indent + f"* {self.project.name}: Run BenchBase (Workloads: {', '.join(self.__WORKLOADS)})"


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
                    RunBenchbase(project, Path(f"rep_{r}.zip"))
                    for r in range(self._REPS)
                ]
            )
        ]

        return analysis_actions

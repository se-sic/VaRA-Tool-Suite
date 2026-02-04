import typing as tp

import benchbuild as bb
from benchbuild.extensions import compiler, run
from benchbuild.utils.actions import Step, Compile, ProjectStep, StepResult
from plumbum import local, ProcessExecutionError

from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.project_util import SupportsBenchbase
from varats.project.varats_project import VProject
from varats.projects.c_projects.postgres import PostgreSQL
from varats.projects.c_projects.sqlite import SQLite
from varats.projects.cpp_projects.mariadb import MariaDB
from varats.report.report import ReportFilepath
from varats.utils.config import get_current_config_id


class RunBenchbase(ProjectStep):
    """Runs the BenchBase benchmark suite."""

    NAME = "RunBenchbase"
    DESCRIPTION = "Run the BenchBase benchmark suite"

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
        self, project: tp.Union[VProject, SupportsBenchbase],
        result_file: ReportFilepath
    ):
        super().__init__(project)
        self.result_file = result_file

    def __call__(self) -> tp.Any:
        self.project: tp.Union[VProject, SupportsBenchbase]

        if not isinstance(self.project, SupportsBenchbase):
            print(f"Project '{self.project.name}' does not support benchbase.")
            self.status = StepResult.ERROR
            return self.status

        benchbase_repo_url = "https://github.com/cmu-db/benchbase.git"
        git = local["git"]

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

        with local.cwd(
            f"benchbase/target/benchbase-{self.project.get_benchbase_profile_name()}"
        ):
            for workload in self.__WORKLOADS:
                print(f"Running workload: {workload}")
                config = ...
                workload_config = self.project.render_workload_config(
                    workload, config
                )

                run_cmd = local["java"]["-jar", "benchbase.jar", "-b", workload,
                                        "-c", workload_config, "--create=true",
                                        "--load=true", "--execute=true"]

                try:
                    # Start the database server
                    self.project.start_database_server()

                    # Run the benchmark
                    bb.watch(run_cmd)()

                    # Stop the database server after benchmark
                    self.project.stop_database_server()
                except ProcessExecutionError as e:
                    print(f"Error running BenchBase workload '{workload}': {e}")
                    self.status = StepResult.ERROR
                    return self.status

                # Zip up results
                try:
                    results_dir = local.path("results")
                    local["zip"]["-r",
                                 self.result_file.full_path(), results_dir]()
                except ProcessExecutionError as e:
                    print(
                        f"Error zipping results for workload '{workload}': {e}"
                    )
                    self.status = StepResult.ERROR
                    return self.status

    def __str__(self, indent: int = 0) -> str:
        return " " * indent + f"* {self.project.name}: Run BenchBase"


class BenchbaseBenchmark(FeatureExperiment, shorthand="BBB"):
    """Runs the BenchBase benchmark suite."""

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        if not isinstance(project, SupportsBenchbase):
            raise TypeError(f"Project {project.name} is not a DatabaseProject.")

        project: tp.Union[VProject, SupportsBenchbase]

        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        result_path = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project,
            project.database_binary(), get_current_config_id(project)
        )

        analysis_actions: tp.List[Step] = [
            Compile(project),
            RunBenchbase(project, result_path)
        ]

        return analysis_actions

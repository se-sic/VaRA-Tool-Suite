"""Experiment that instruments a project with verification instrumentation that
is used during execution to check if regions are correctly opend/closed."""
import os
import textwrap
import typing as tp

import benchbuild.command as bbcmd
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
)
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.report import FileStatusExtension as FSE
from varats.utils.git_util import ShortCommitHash

# TODO: merge this with feature runner experiment


class RunAndVerifyInstrumentedProject(actions.ProjectStep):  #type: ignore

    NAME = "RunAndVerifyInstrumentedProject"
    DESCRIPTION = "foo"

    def __init__(
        self, project: VProject, experiment_handle: ExperimentHandle
    ) -> None:
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.run_verifier()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumentation verifier", indent * " "
        )

    def run_verifier(self) -> actions.StepResult:

        project: VProject = self.project

        print(f"PWD {os.getcwd()}")

        vara_result_folder = get_varats_result_folder(project)
        for binary in project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            result_file = self.__experiment_handle.get_file_name(
                self.__experiment_handle.report_spec().main_report.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=ShortCommitHash(project.version_of_primary),
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            # with local.cwd(local.path(project.source_of_primary)):  # / ".."):
            with local.cwd(local.path(project.builddir)):
                print(f"Currenlty at {local.path(project.source_of_primary)}")
                print(f"Bin path {binary.path}")

                # executable = local[f"{binary.path}"]

                with local.env(
                    VARA_TRACE_FILE=f"{vara_result_folder}/{result_file}"
                ):

                    workload = \
                        "/scratch/sattlerf/countries-land-1km.geo.json"

                    # Get jobs from project
                    jobs = bbcmd.filter_job_index(project.jobs, None)
                    print(f"{jobs=}")
                    project_commands = bbcmd.prepare_project_commands(
                        project, jobs
                    )
                    print(f"{project_commands=}")
                    res = [job() for job in project_commands]
                    print(f"{res=}")

                    # print(project.jobs)
                    # for job in project.jobs.items():
                    #     print(f"job: {str(job)}")
                    #     for wl in job[1]:
                    #         print(f"wl: {wl}")

                    #         print(f"Here PWD {os.getcwd()}")

                    #         print(f"{wl.path=}")
                    #         # wl()
                    #         cmd = wl.as_plumbum()
                    #         print(cmd["-k", "--verbose"])
                    #         cmd("-k", "--verbose")

                    # inject_binary_names(jobs, binary)

                    # wjobs = wrap_jobs_to_run(jobs)
                    # exec_run_jobs(wjobs)

                    # TODO: figure out how to handle workloads
                    # binary("-f", "-k", workload)

                    # TODO: figure out how to handle different configs
                    # executable("--slow")
                    # executable()

        return actions.StepResult.OK


class RunInstrVerifier(VersionExperiment, shorthand="RIV"):
    """Test runner for feature performance."""

    NAME = "RunInstrVerifier"

    REPORT_SPEC = ReportSpecification(InstrVerifierReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = "instr_verify"

        fm_provider = FeatureModelProvider.create_provider_for_project(
            type(project)
        )
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # Sets FM model flags
        project.cflags += [
            "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"
        ]
        # Sets vara tracing flags
        project.cflags += [
            "-fsanitize=vara", f"-fvara-instr={instr_type}", "-flto",
            "-fuse-ld=lld", "-Wl,-plugin-opt=save-temps"
        ]
        project.ldflags += ["-flto"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)  #\
        #<< time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self)  # \
        #<< run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunAndVerifyInstrumentedProject(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

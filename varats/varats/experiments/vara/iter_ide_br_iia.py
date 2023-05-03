"""
Implements the basic blame report experiment.

The experiment analyses a project with VaRA's blame analysis and generates a
BlameReport.
"""

import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild import Project
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.utils import actions
from benchbuild.utils.cmd import time, mkdir, touch, opt
from benchbuild.utils.requirements import Requirement, SlurmMem
from plumbum import RETCODE

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.blame_report import BlameTaintScope
from varats.data.reports.phasar_iter_ide import PhasarIterIDEStatsReport
from varats.experiment.experiment_util import (
    ZippedExperimentSteps,
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import (
    get_bc_cache_actions,
    get_cached_bc_file_path,
    BCFileExtensions,
)
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_paths,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class IterIDEBRIIAKind(Enum):
    value: str

    JF1 = "vara-BR-JF1"
    JF2 = "vara-BR-JF2"
    JF2S = "vara-BR-JF2S"
    Old = "vara-BR-Old"

    JF1WithGC = "vara-BR-JF1-GC"
    JF2WithGC = "vara-BR-JF2-GC"

    JF1WithStats = "vara-BR-JF1-stats"
    JF2WithStats = "vara-BR-JF2-stats"

    def __str__(self) -> str:
        return f"{self.value}"


class IterIDEBlameReportGeneration(actions.ProjectStep):  # type: ignore
    """Analyse a project with VaRA and generate a BlameReport."""

    NAME = "PhasarIterIDEBRIIAEx"
    DESCRIPTION = "Analyses the bitcode with -vara-BR-* of VaRA."

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper,
        blame_taint_scope: BlameTaintScope, solver_config: IterIDEBRIIAKind
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary
        self.__blame_taint_scope = blame_taint_scope
        self.__solver_config = solver_config

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.

        Flags used:
            * -vara-BR: to run a commit flow report
            * -yaml-report-outfile=<path>: specify the path to store the results
        """

        analysis_kind_str = str(self.__solver_config)

        tmp_dir /= f"new_iia_{analysis_kind_str}"
        mkdir("-p", tmp_dir)

        opt_params = [
            "--enable-new-pm=0", "-vara-BD", "-" + analysis_kind_str,
            "-vara-init-commits", "-vara-rewriteMD",
            "-vara-git-mappings=" + ",".join([
                f'{repo}:{path}' for repo, path in
                get_local_project_git_paths(self.project.name).items()
            ]), "-vara-use-phasar",
            f"-vara-blame-taint-scope={self.__blame_taint_scope.name}",
            get_cached_bc_file_path(
                self.project, self.__binary, [
                    BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                    BCFileExtensions.BLAME
                ]
            )
        ]

        run_cmd = wrap_unlimit_stack_size(opt[opt_params])
        result_file = tmp_dir / f"new_iia_{self.__num}.txt"
        run_cmd = time['-v', '-o', f"{result_file}", run_cmd]

        ret_code = run_cmd & RETCODE
        if ret_code == 137:
            print("Found OOM (new)")
            return actions.StepResult.OK

        if ret_code != 0:
            error_file = tmp_dir / f"new_iia_{self.__num}_err_{ret_code}.txt"
            touch(error_file)
            return actions.StepResult.ERROR

        return actions.StepResult.OK


class IterIDEBlameReportExperiment(VersionExperiment, shorthand="IterIDEBRIA"):
    """Generates a blame report of the project(s) specified in the call."""

    NAME = "IterIDEGenerateBlameReport"

    REPORT_SPEC = ReportSpecification(PhasarIterIDEStatsReport)
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]

    CONTAINER = ContainerImage().run("apt", "install", "-y", "time")

    BLAME_TAINT_SCOPE = BlameTaintScope.COMMIT

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
        ]

        BE.setup_basic_blame_experiment(self, project, PhasarIterIDEStatsReport)

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project,
            bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        # Only consider the main/first binary
        print(f"{project.name}")
        if len(project.binaries) < 1:
            return []

        binary = project.binaries[0]
        result_file = create_new_success_result_filepath(
            self.get_handle(), self.REPORT_SPEC.main_report, project, binary
        )

        # analysis_actions = []

        # analysis_actions += get_bc_cache_actions(
        #     project,
        #     bc_file_extensions=bc_file_extensions,
        #     extraction_error_handler=create_default_compiler_error_handler(
        #         self.get_handle(), project, self.REPORT_SPEC.main_report
        #     )
        # )

        reps = range(0, 1)

        analysis_actions.append(
            ZippedExperimentSteps(
                result_file, [
                    *[
                        IterIDEBlameReportGeneration(
                            project, rep, binary, self.BLAME_TAINT_SCOPE,
                            solver_config
                        ) for rep in reps for solver_config in IterIDEBRIIAKind
                    ]
                ]
            )

            # BlameReportGeneration(
            #     project, self.get_handle(), self.BLAME_TAINT_SCOPE
            # )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class IterIDEBlameReportExperimentRegion(
    IterIDEBlameReportExperiment, shorthand="IterIDEBRER"
):
    """Generates a blame report with region scoped taints."""

    NAME = "IterIDEGenerateBlameReportRegion"
    BLAME_TAINT_SCOPE = BlameTaintScope.REGION


class IterIDEBlameReportExperimentCommitInFunction(
    IterIDEBlameReportExperiment, shorthand="IterIDEBRECIF"
):
    """Generates a blame report with commit-in-function scoped taints."""

    NAME = "IterIDEGenerateBlameReportCommitInFunction"
    BLAME_TAINT_SCOPE = BlameTaintScope.COMMIT_IN_FUNCTION

"""Implements experiments for evaluating different incremental analysis
approaches."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import mkdir, phasar_globals
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    get_varats_result_folder,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    get_default_compile_error_wrapped,
)
from varats.experiment.wllvm import (
    get_cached_bc_file_path,
    BCFileExtensions,
    get_bc_cache_actions,
    RunWLLVM,
)
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification
from varats.utils.settings import bb_cfg


class RunAnalysisBase(actions.Step):

    def __init__(
        self,
        project: Project,
        # analysis_command  # TODO: pass command or flags?
        run_incrementally: bool,
        run_taint_analysis: bool
    ) -> None:
        super().__init__(obj=project, action_fn=self.run_analysis)

        self.__run_inc = run_incrementally
        self.__run_taint_analysis = run_taint_analysis

    def run_analysis(self) -> actions.StepResult:
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj

        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            pass

        return actions.StepResult.OK


class RunTypeStateAnalysisWPA(RunAnalysisBase):

    NAME = "RunTypeStateAnalysisWPA"
    DESCRIPTION = ""  # TODO:


class RunTaintAnalysisWPA(RunAnalysisBase):

    NAME = "RunTaintAnalysisWPA"
    DESCRIPTION = ""  # TODO:


class RunTypeStateAnalysisINC(RunAnalysisBase):

    NAME = "RunTypeStateAnalysisINC"
    DESCRIPTION = ""  # TODO:


class RunTaintAnalysisINC(RunAnalysisBase):

    NAME = "RunTaintAnalysisINC"
    DESCRIPTION = ""  # TODO:


# TODO: infos to gather:
#       * RQ1: Analysis results WPA vs INC
#           - need comparision
#       * RQ2:
#           - Fine grained analysis speed (parts) -> output file
#           - Put everything into one file or multiples in a spec
#           - Diff size selection? -> choose "right" revisions?

# TODO: should we handle the diff size with a specific selection heuristic?
# TODO: all in one experiment? Should be possible I guess?


class PrecisionComparisionBase(VersionExperiment, shorthand=""):

    NAME = "GlobalsComparision"

    REPORT_SPEC = ReportSpecification(GlobalsReportWith, GlobalsReportWithout)

    def __init__(self, revision_step_with: int) -> None:
        pass

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
        ]

        analysis_actions = get_bc_cache_actions(
            project, bc_file_extensions,
            create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(actions.Compile(project))

        # Clean up the generated files afterwards
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class IncrementalAnalysisPrecisionComparisionS1(
    PrecisionComparisionBase, shorthand="IncAPCs1"
):

    def __init__(self) -> None:
        super().__init__(1)


class IncrementalAnalysisPrecisionComparisionS5(
    PrecisionComparisionBase, shorthand="IncAPCs5"
):

    def __init__(self) -> None:
        super().__init__(5)

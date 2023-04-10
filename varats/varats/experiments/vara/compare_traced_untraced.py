"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
from abc import abstractmethod
import typing as tp

from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    create_new_success_result_filepath, ZippedExperimentSteps
)
from varats.report.report import ReportSpecification
from varats.experiments.base.time_workloads import TimeProjectWorkloads
from varats.report.gnu_time_report import WLTimeReportAggregate

from varats.project.varats_project import VProject

from varats.experiments.vara.dynamic_overhead_analysis import Runner

MEASUREMENT_REPS = 5


class RunUntraced(Runner, shorthand="RU"):
    """Build and run the untraced version of the binary"""

    NAME = "RunUntraced"
    REPORT_SPEC = ReportSpecification(WLTimeReportAggregate)

    def get_analysis_actions(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        actions = []
        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )
            actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimeProjectWorkloads(project, num, binary)
                        for num in range(MEASUREMENT_REPS)
                    ]
                )
            )
        return actions


class RunTraced(RunUntraced, shorthand="RT"):
    """Build and run the traced version of the binary"""

    NAME = "RunTraced"

    @property
    @abstractmethod
    def optimizer_policy(self):
        return "none"

    def set_vara_flags(self, project: VProject) -> VProject:
        instr_type = "trace_event"  # trace_event

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type)

        project.cflags += [
            "-mllvm", f"-vara-optimizer-policy={self.optimizer_policy}"
        ]

        project.ldflags += self.get_vara_tracing_ldflags()

        return project


class RunTracedNaive(RunTraced, shorthand=RunTraced.SHORTHAND + "N"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedNaive"

    @property
    @abstractmethod
    def optimizer_policy(self):
        return "naive"


class RunTracedAlternating(RunTraced, shorthand=RunTraced.SHORTHAND + "A"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedAlternating"

    @property
    @abstractmethod
    def optimizer_policy(self):
        return "alternating"

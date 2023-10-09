"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
from abc import abstractmethod
import typing as tp

from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    create_new_success_result_filepath, ZippedExperimentSteps
)
from varats.experiment.workload_util import WorkloadCategory
from varats.report.report import ReportSpecification
from varats.experiments.base.time_workloads import TimeProjectWorkloads
from varats.report.gnu_time_report import WLTimeReportAggregate

from varats.project.varats_project import VProject

from varats.experiments.vara.dynamic_overhead_analysis import OptimizerPolicyType
from varats.experiments.vara.feature_experiment import FeatureExperiment, FeatureInstrType
from varats.experiments.vara.multi_compile_experiment import VaryingStartingBudgetExperiment

MEASUREMENT_REPS = 1


class RunUntraced(FeatureExperiment, shorthand="RU"):
    """Build and run the untraced version of the binary"""

    NAME = "RunUntraced"

    REPORT_SPEC = ReportSpecification(WLTimeReportAggregate)

    def actions_for_project(
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
                        TimeProjectWorkloads(
                            project,
                            num,
                            binary,
                            categories=[
                                WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL
                            ]
                        ) for num in range(MEASUREMENT_REPS)
                    ]
                )
            )

        return self.get_common_tracing_actions(
            project, FeatureInstrType.NONE, actions, save_temps=True
        )


class RunTraced(FeatureExperiment, shorthand="RT"):
    """Build and run the traced version of the binary"""

    NAME = "RunTraced"
    REPORT_SPEC = ReportSpecification(WLTimeReportAggregate)

    @property
    @abstractmethod
    def optimizer_policy(self) -> OptimizerPolicyType:
        return OptimizerPolicyType.NONE

    @property
    @abstractmethod
    def budget(self) -> tp.Optional[int]:
        return None

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:

        project.cflags += [
            "-mllvm", f"-vara-optimizer-policy={self.optimizer_policy.value}"
        ]

        if self.budget is not None:
            project.cflags += [
                "-mllvm",
                f"-vara-optimizer-starting-budget={self.budget}",
            ]

        actions = []
        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )
            actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        TimeProjectWorkloads(
                            project,
                            num,
                            binary,
                            categories=[
                                WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL
                            ]
                        ) for num in range(MEASUREMENT_REPS)
                    ]
                )
            )

        return self.get_common_tracing_actions(
            project, FeatureInstrType.TEF, actions, save_temps=True
        )


class RunTracedNaive(RunTraced, shorthand=RunTraced.SHORTHAND + "N"):
    """Build and run the traced version of the binary"""

    NAME = "RunTracedNaive"

    @property
    @abstractmethod
    def optimizer_policy(self) -> OptimizerPolicyType:
        return OptimizerPolicyType.NAIVE


class RunTracedNaive20(RunTracedNaive, shorthand=RunTracedNaive.SHORTHAND + "20"):
    NAME = "RunTracedNaive20"

    @property
    @abstractmethod
    def budget(self) -> int:
        return 20


class RunTracedNaive40(RunTracedNaive, shorthand=RunTracedNaive.SHORTHAND + "40"):
    NAME = "RunTracedNaive40"

    @property
    @abstractmethod
    def budget(self) -> int:
        return 40


class RunTracedNaive60(RunTracedNaive, shorthand=RunTracedNaive.SHORTHAND + "60"):
    NAME = "RunTracedNaive60"

    @property
    @abstractmethod
    def budget(self) -> int:
        return 60


class RunTracedNaive80(RunTracedNaive, shorthand=RunTracedNaive.SHORTHAND + "80"):
    NAME = "RunTracedNaive80"

    @property
    @abstractmethod
    def budget(self) -> int:
        return 80


class RunTracedNaive100(RunTracedNaive, shorthand=RunTracedNaive.SHORTHAND + "100"):
    NAME = "RunTracedNaive100"

    @property
    @abstractmethod
    def budget(self) -> int:
        return 100


# class RunTracedAlternating(RunTraced, shorthand=RunTraced.SHORTHAND + "A"):
#     """Build and run the traced version of the binary"""

#     NAME = "RunTracedAlternating"

#     @property
#     @abstractmethod
#     def optimizer_policy(self) -> OptimizerPolicyType:
#         return OptimizerPolicyType.ALTERNATING


# class RunTracedBudget(VaryingStartingBudgetExperiment, shorthand="RTB"):
#     """Build and run the traced version of the binary"""

#     NAME = "RunTracedBudget"
#     REPORT_SPEC = ReportSpecification(WLTimeReportAggregate)

#     @property
#     @abstractmethod
#     def optimizer_policy(self) -> OptimizerPolicyType:
#         return OptimizerPolicyType.NONE

#     def actions_for_project(
#         self, project: VProject
#     ) -> tp.MutableSequence[actions.Step]:

#         project.cflags += [
#             "-mllvm",
#             f"-vara-optimizer-policy={self.optimizer_policy.value}",
#         ]

#         actions = []
#         for binary in project.binaries:
#             result_filepath = create_new_success_result_filepath(
#                 self.get_handle(),
#                 self.get_handle().report_spec().main_report, project, binary
#             )
#             actions.append(
#                 ZippedExperimentSteps(
#                     result_filepath, [
#                         TimeProjectWorkloads(
#                             project,
#                             num,
#                             binary,
#                             categories=[
#                                 WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL
#                             ]
#                         ) for num in range(MEASUREMENT_REPS)
#                     ]
#                 )
#             )

#         return self.get_common_tracing_actions(
#             project, FeatureInstrType.TEF, actions, save_temps=True
#         )

# class RunTracedNaiveBudget(
#     RunTracedBudget, shorthand=RunTracedBudget.SHORTHAND + "N"
# ):
#     """Build and run the traced version of the binary"""

#     NAME = "RunTracedNaiveBudget"

#     @property
#     @abstractmethod
#     def optimizer_policy(self) -> OptimizerPolicyType:
#         return OptimizerPolicyType.NAIVE

# class RunTracedAlternatingBudget(
#     RunTracedBudget, shorthand=RunTracedBudget.SHORTHAND + "A"
# ):
#     """Build and run the traced version of the binary"""

#     NAME = "RunTracedAlternatingBudget"

#     @property
#     @abstractmethod
#     def optimizer_policy(self) -> OptimizerPolicyType:
#         return OptimizerPolicyType.ALTERNATING

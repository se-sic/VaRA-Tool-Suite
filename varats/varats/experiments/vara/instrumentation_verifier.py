"""Experiment that instruments a project with verification instrumentation that
is used during execution to check if regions are correctly opend/closed."""
import typing as tp

from benchbuild.utils import actions
from varats.experiment.workload_util import WorkloadCategory

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.experiments.vara.multi_compile_experiment import VaryingStartingBudgetExperiment


class RunInstrVerifier(FeatureExperiment, shorthand="RIV"):
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
        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(
                project,
                self.get_handle(),
                report_file_ending="ivr",
                workload_categories=[
                    WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return self.get_common_tracing_actions(
            project,
            FeatureInstrType.VERIFY,
            analysis_actions,
            save_temps=True,
            instruction_threshold=0
        )


class RunInstrVerifierBudget(VaryingStartingBudgetExperiment, shorthand="RIVB"):
    """Test runner for feature performance."""

    NAME = "RunInstrVerifierBudget"

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

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(
                project,
                self.get_handle(),
                report_file_ending="ivr",
                workload_categories=[
                    WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL
                ],
            )
        )
        analysis_actions.append(actions.Clean(project))

        return self.get_common_tracing_actions(
            project,
            FeatureInstrType.VERIFY,
            analysis_actions,
            save_temps=True,
            instruction_threshold=0
        )

"""Experiment that instruments a project with verification instrumentation that
is used during execution to check if regions are correctly opend/closed."""
import typing as tp

from benchbuild.extensions import compiler, run
from benchbuild.utils import actions

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import get_default_compile_error_wrapped
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


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
        instr_type = "instr_verify"

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type, True)

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self)

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

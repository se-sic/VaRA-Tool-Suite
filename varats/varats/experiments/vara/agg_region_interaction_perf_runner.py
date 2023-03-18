"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import typing as tp

from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions

from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReport,
)
from varats.experiment.experiment_util import get_default_compile_error_wrapped
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class AggregatedRegionInteractionPerfRunner(
    FeatureExperiment, shorthand="ARPR"
):
    """Test runner for aggregated region interaction performance."""

    NAME = "RunAggRegionPerf"

    REPORT_SPEC = ReportSpecification(PerfInfluenceTraceReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = FeatureInstrType.PERF_INFLUENCE_TRACE

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(
            instr_type, project=project
        )

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, PerfInfluenceTraceReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

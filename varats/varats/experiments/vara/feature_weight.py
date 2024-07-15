"""Implements an experiment that times the execution of all project binaries."""
import typing as tp

from benchbuild.extensions import compiler, run
from benchbuild.utils import actions

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    WithUnlimitedStackSize,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class WeightRegionsCountRec(FeatureExperiment, shorthand="WAR"):
    """Generates Weight report files for Recursive weight function."""

    NAME = "WeightAnalysisRecursive"

    REPORT_SPEC = ReportSpecification(InstrVerifierReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        project.cflags += self.get_vara_feature_cflags(project)

        # change the featureInstrType to verify
        project.cflags += self.get_vara_tracing_cflags(
            FeatureInstrType.TEF, instruction_threshold=1
        )

        project.cflags += [
            "-fvara-weight-opt=recursive",
            "-01",
            "-g0",
            "-mllvm",
            "--vara-use-phasar"
        ]

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize()


        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(
                project, self.get_handle(), report_file_ending="ivr"
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

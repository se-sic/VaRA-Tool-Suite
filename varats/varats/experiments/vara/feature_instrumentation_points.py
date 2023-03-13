"""Collect information about feature instrumentation points using VaRA's
InstrumentationPointPrinter utility pass."""

import typing as tp

import benchbuild as bb
from benchbuild import Project
from benchbuild.extensions import compiler
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from plumbum import local

from varats.data.reports.feature_instrumentation_points_report import (
    FeatureInstrumentationPointsReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    WithUnlimitedStackSize,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    Extract,
    RunWLLVM,
    get_cached_bc_file_path,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class CollectInstrumentationPoints(actions.ProjectStep):  # type: ignore
    """Step that collects instrumentation points using VaRA's instrumentation
    point printer."""

    NAME = "CollectInstrumentationPoints"
    DESCRIPTION = (
        "Collect instrumentation points using VaRA's instrumentation point"
        "printer"
    )

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, FeatureInstrumentationPointsReport,
                self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-IPP", "-o", "/dev/null",
                get_cached_bc_file_path(
                    self.project, binary,
                    [BCFileExtensions.DEBUG, BCFileExtensions.FEATURE]
                )
            ]

            with local.env(IPP_OUTFILE=result_file.full_path()):
                bb.watch(opt)(opt_params)

        return actions.StepResult.OK


class FeatureInstrumentationPoints(FeatureExperiment, shorthand="FIP"):
    """Collect information about feature instrumentation points using VaRA's
    InstrumentationPointPrinter utility pass."""

    NAME = "FeatureInstrumentationPoints"

    REPORT_SPEC = ReportSpecification(FeatureInstrumentationPointsReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        analysis_actions = self.get_common_tracing_actions(
            project, FeatureInstrType.NONE, [
                Extract(
                    project, [BCFileExtensions.DEBUG, BCFileExtensions.FEATURE]
                ),
                CollectInstrumentationPoints(project, self.get_handle())
            ]
        )

        project.cflags = self.get_vara_feature_cflags(project)
        project.cflags.append("-g")  # debug info for source code locations
        project.ldflags = []

        # Transfer the whole project into LLVM-IR.
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << WithUnlimitedStackSize()

        return analysis_actions

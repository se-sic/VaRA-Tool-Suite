"""Module defining helpers for feature performance experiments."""

import typing as tp
from enum import Enum

from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.extensions import time as bbtime
from benchbuild.utils import actions

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
)
from varats.provider.feature.feature_model_provider import (
    FeatureModelNotFound,
    FeatureModelProvider,
)
from varats.report.report import ReportSpecification


class InstrumentationType(Enum):
    """Type of instrumentation to be used in experiment."""

    NONE = "print"
    """Don't add any instrumentation."""
    PRINT = "print"
    """Print trace to stdout."""
    TEF = "trace_event"
    """Write trace event file."""
    USDT = "usdt"
    """Insert USDT probes."""


def feature_perf_compiler_options(
    instrumentation: InstrumentationType, project: Project,
    use_feature_model: bool
) -> tp.List[str]:
    """Returns compiler options for feature performance experiment."""

    if instrumentation is InstrumentationType.NONE:
        return []

    cflags = [
        "-fvara-feature", "-fsanitize=vara",
        f"-fvara-instr={instrumentation.value}", "-flto", "-fuse-ld=lld"
    ]

    if use_feature_model:
        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        cflags.append(f"-fvara-fm-path={fm_path.absolute()}")

    return cflags


def feature_perf_linker_options(
    instrumentation: InstrumentationType
) -> tp.List[str]:
    """Returns linker options for feature performance experiment."""

    return [] if instrumentation is InstrumentationType.NONE else ["-flto"]


class FeaturePerfExperiment(
    VersionExperiment, shorthand="ChangeExperimentName"
):
    """
    Base class for feature performance experiments.

    Configures common options shared among these experiments.
    """

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self,
        project: Project,
        instrumentation: InstrumentationType = InstrumentationType.NONE,
        analysis_actions: tp.Optional[tp.Iterable[actions.Step]] = None,
        use_feature_model: bool = False
    ) -> tp.MutableSequence[actions.Step]:
        """
        Get the actions a project wants to run.

        `additional_analysis_actions` - Analysis actions to run between compile
        and clean.
        """

        if analysis_actions is None:
            analysis_actions = []

        # compiler and linker options
        project.cflags += feature_perf_compiler_options(
            instrumentation, project, use_feature_model
        )
        project.ldflags += feature_perf_linker_options(instrumentation)

        # runtime and compiler extensions
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << bbtime.RunWithTime()
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # project actions
        project_actions = []
        project_actions.append(actions.Compile(project))
        project_actions.extend(analysis_actions)
        project_actions.append(actions.Clean(project))

        # compile error handler
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project,
            self.report_spec().main_report
        )

        return project_actions

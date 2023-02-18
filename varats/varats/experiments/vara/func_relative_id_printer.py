"""Implements experiment for VaRA's FuncRelativeIDPrinter utility pass."""

import typing as tp
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.actions import Compile, StepResult
from benchbuild.utils.cmd import cp
from plumbum import local

from varats.data.reports.vara_fridpp_report import VaraFRIDPPReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    WithUnlimitedStackSize,
    create_new_success_result_filepath,
    ExperimentHandle,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class CompileWithFRIDPPOutput(Compile):
    NAME = "COMPILE_WITH_FRIDPP_OUTPUT"
    DESCRIPTION = "Compile the project"

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> StepResult:
        result_filepath = create_new_success_result_filepath(
            self.__experiment_handle,
            self.__experiment_handle.report_spec().main_report, self.project,
            self.project.binaries[0], None
        )

        with TemporaryDirectory() as tmp_dir:
            local_fridpp_path = Path(
                tmp_dir
            ) / f"fridpp_{self.project.version_of_primary}.txt"
            with local.env(VARA_FRIDPP_FILE=local_fridpp_path):
                status_code = super().__call__()
                cp(local_fridpp_path, result_filepath)
                return status_code


class FuncRelativeIDPrinter(VersionExperiment, shorthand="FRIDPP"):
    """Experiment, which uses VaRA's FuncRelativeIDPrinter utility pass to
    collect function-relative IDs of VaRA's feature regions."""

    NAME = "VaraFRIDPP"

    REPORT_SPEC = ReportSpecification(VaraFRIDPPReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        project.cflags += FeatureExperiment.get_vara_tracing_cflags(
            "rit_trace_event"
        )
        project.cflags += ["-fvara-GB", "-Wl,-mllvm,--vara-ifridpp"]

        project.ldflags += FeatureExperiment.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, VaraFRIDPPReport
        )

        analysis_actions = []

        analysis_actions.append(
            CompileWithFRIDPPOutput(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

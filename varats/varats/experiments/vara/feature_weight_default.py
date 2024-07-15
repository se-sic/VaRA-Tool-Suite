"""Implements an experiment that times the execution of all project binaries."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import time
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.report.report import ReportSpecification




class WeightRegionsCount(VersionExperiment, shorthand="WAD"):
    """Generates Weight report files."""

    NAME = "WeightAnalysisDefault"

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
            "-fvara-weight-opt=default",
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

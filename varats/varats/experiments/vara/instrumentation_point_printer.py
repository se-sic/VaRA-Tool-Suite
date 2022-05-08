"""Implements experiment for VaRA's InstrumentationPointPrinter utility pass."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.reports.vara_ipp_report import VaraIPPReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    get_varats_result_folder,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    Extract,
    RunWLLVM,
    get_cached_bc_file_path,
)
from varats.provider.feature.feature_model_provider import (
    FeatureModelNotFound,
    FeatureModelProvider,
)
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification


class CollectInstrumentationPoints(actions.Step):  # type: ignore
    """Runs utility pass on LLVM-IR to extract instrumentation point
    information."""

    NAME = "CollectInstrumentationPoints"
    DESCRIPTION = "Runs utility pass on LLVM-IR to extract instrumentation " \
        "point information."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle

    def analyze(self) -> actions.StepResult:
        """Run VaRA-IPP utility pass and extract instrumentation point
        information."""
        project = self.obj

        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            result_file = self.__experiment_handle.get_file_name(
                VaraIPPReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            # Need the following passes:
            # - vara-PFTDD to generate feature regions
            # - vara-IPP (Instrumentation Point Printer)
            opt_params = [
                "--vara-PTFDD", "-vara-IPP", "-o", "/dev/null",
                get_cached_bc_file_path(
                    project, binary,
                    [BCFileExtensions.DEBUG, BCFileExtensions.FEATURE]
                )
            ]

            # Store the collected information in report.
            run_cmd = opt[opt_params] > str(
                vara_result_folder / str(result_file)
            )

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, VaraIPPReport,
                    Path(vara_result_folder)
                )
            )

        return actions.StepResult.OK


class InstrumentationPointPrinter(VersionExperiment, shorthand="IPP"):
    """Experiment, which uses VaRA's InstrumentationPointPrinter utility pass to
    collect source code locations of instrumentation points of VaRA's feature
    regions."""

    NAME = "VaraIPP"

    REPORT_SPEC = ReportSpecification(VaraIPPReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # We need debug info to later determine source code locations in a
        # utility pass. Also, include feature information.
        project.cflags += [
            "-g", "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"
        ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s). We want to
        # transfer the whole project into LLVM-IR.
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        bc_file_extensions = [BCFileExtensions.DEBUG, BCFileExtensions.FEATURE]

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(Extract(project, bc_file_extensions))
        analysis_actions.append(
            CollectInstrumentationPoints(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

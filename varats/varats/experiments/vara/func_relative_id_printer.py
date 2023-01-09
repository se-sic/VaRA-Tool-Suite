"""Implements experiment for VaRA's FuncRelativeIDPrinter utility pass."""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.reports.vara_fridpp_report import VaraFRIDPPReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    get_varats_result_folder,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    Extract,
    RunWLLVM,
    get_cached_bc_file_path,
)
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelNotFound,
    FeatureModelProvider,
)
from varats.report.report import ReportSpecification


class CollectFuncRelativeIDs(actions.ProjectStep):  # type: ignore
    """Runs utility pass on LLVM-IR to extract function relative ID
    information."""

    NAME = "CollectFuncRelativeIDs"
    DESCRIPTION = "Runs utility pass on LLVM-IR to extract function-relative" \
        "ID information."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """Run VaRA-FRIDPP utility pass and extract function-relative ID
        information."""
        vara_result_folder = get_varats_result_folder(self.project)

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, VaraFRIDPPReport, self.project, binary
            )

            # Need the following passes:
            # - vara-PFTDD to generate feature regions
            # - vara-FRIDPP (Function-Relative ID Printer)
            opt_params = [
                "--enable-new-pm=0", "--vara-PTFDD", "-vara-FRIDPP", "-o",
                "/dev/null",
                get_cached_bc_file_path(
                    self.project, binary,
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
                    self.__experiment_handle, self.project, VaraFRIDPPReport
                )
            )

        return actions.StepResult.OK


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
            CollectFuncRelativeIDs(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

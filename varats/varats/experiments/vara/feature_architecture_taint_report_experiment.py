"""Implements an experiment which generates an architecture report for the
project."""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.architecture_report import (
    ArchitectureTaintReport,
    FeatureArchitectureTaintReport,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    get_varats_result_folder,
    wrap_unlimit_stack_size,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
    get_cached_bc_file_path,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.provider.architecture.architecture_model_provider import (
    ArchitectureModelProvider,
)
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class FeatureArchitectureTaintAnalysis(actions.ProjectStep):  # type: ignore
    """Analyses a project's architecture with VaRA and generates a report."""

    NAME = "ArchitectureTaintAnalysis"
    DESCRIPTION = "Analyses the bitcode with -vara-arch of VaRA."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        config_id = get_current_config_id(self.project)
        if not self.project:
            return actions.StepResult.ERROR
        project = self.project

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = get_varats_result_folder(project)
        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, FeatureArchitectureTaintReport,
                self.project, binary, config_id
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-AD", "-vara-PTFDD", "-vara-FBFD",
                "-vara-FATR", "-vara-use-phasar",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT,
                        BCFileExtensions.TBAA,
                        BCFileExtensions.FEATURE,
                        BCFileExtensions.ARCH,
                    ]
                )
            ]

            run_cmd = opt[opt_params]
            run_cmd = wrap_unlimit_stack_size(run_cmd)
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project,
                    FeatureArchitectureTaintReport
                )
            )

        return actions.StepResult.OK


class FeatureArchitectureTaintReportExperiment(
    VersionExperiment, shorthand="FATRE"
):
    """Generates an Architecture report file."""

    NAME = "GenerateFeatureArchitectureTaintReport"
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]
    REPORT_SPEC = ReportSpecification(FeatureArchitectureTaintReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # FeatureModelProvider
        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise FeatureModelNotFound(project, None)

        fm_path = fm_provider.get_feature_model_path(project.name)

        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << RunWLLVM() \
                                     << run.WithTimeout()
        am_provider = ArchitectureModelProvider.create_provider_for_project(
            project
        )
        if am_provider is None:
            raise FeatureModelNotFound(project, None)
        am_path = am_provider.get_architecture_model_path()
        project.cflags += [
            "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}",
            "-fvara-arch", "-Xclang", "-disable-llvm-optzns", "-O1", "-g0"
        ]
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.FEATURE,
            BCFileExtensions.ARCH,
        ]
        extraction_error_handler = create_default_compiler_error_handler(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )
        analysis_actions = get_bc_cache_actions(
            project, bc_file_extensions, extraction_error_handler
        )
        analysis_actions.append(
            FeatureArchitectureTaintAnalysis(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

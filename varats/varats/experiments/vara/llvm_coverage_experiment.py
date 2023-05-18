""""Coverage experiment."""

import json
import typing as tp
from pathlib import Path
from shutil import copy

from benchbuild import Project
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from plumbum import local

from varats.data.reports.llvm_coverage_report import CoverageReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    get_extra_config_options,
    get_current_config_id,
    wrap_unlimit_stack_size,
    ZippedExperimentSteps,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    BCFileExtensions,
    Extract,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelNotFound,
    FeatureModelProvider,
)
from varats.report.report import ReportSpecification

BC_FILE_EXTENSIONS = [
    BCFileExtensions.NO_OPT, BCFileExtensions.TBAA, BCFileExtensions.FEATURE
]
TIMEOUT = "1h"


class GenerateCoverage(actions.ProjectStep):  # type: ignore
    """GenerateCoverage experiment."""

    NAME = "GenerateCoverage"
    DESCRIPTION = (
        "Runs the instrumented binary file in \
        order to obtain the coverage information."
    )

    project: VProject

    def __init__(
        self,
        project: Project,
        binary: ProjectBinaryWrapper,
        workload_cmds: tp.List[ProjectCommand],
        _experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.binary = binary
        self.__workload_cmds = workload_cmds
        self.__experiment_handle = _experiment_handle

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Runs project and export coverage information + bc files."""
        with local.cwd(self.project.builddir):
            if not self.__workload_cmds:
                # No workload to execute.
                # Fail because we don't get any coverage data
                return actions.StepResult.ERROR
            for prj_command in self.__workload_cmds:
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                extra_args = get_extra_config_options(self.project)
                profdata_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.profdata"
                )
                json_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.json"
                )

                profile_raw_name = f"{prj_command.path.name}.profraw"
                run_cmd = pb_cmd.with_env(LLVM_PROFILE_FILE=profile_raw_name)
                llvm_profdata = local["llvm-profdata"]
                llvm_cov = local["llvm-cov"]
                llvm_cov = llvm_cov["export",
                                    f"--instr-profile={profdata_name}",
                                    Path(self.project.source_of_primary) /
                                    self.binary.path]

                with cleanup(prj_command):
                    run_cmd(*extra_args)
                    llvm_profdata(
                        "merge", profile_raw_name, "-o", profdata_name
                    )
                    (llvm_cov > str(json_name))()

                    # Add absolute path to json to compute
                    # relative filenames later in the report
                    with open(json_name) as file:
                        coverage = json.load(file)

                    coverage["absolute_path"] = str(
                        Path(self.project.source_of_primary).resolve()
                    )

                    with open(json_name, "w") as file:
                        json.dump(coverage, file)

                # BC file handling
                bc_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.bc"
                )
                ptfdd_report_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".ptfdd"
                )

                bc_path = get_cached_bc_file_path(
                    self.project, self.binary, BC_FILE_EXTENSIONS
                )
                copy(bc_path, bc_name)

                opt_command = opt["-enable-new-pm=0", "-vara-PTFDD",
                                  "-vara-export-feature-dbg",
                                  #"-vara-view-IRegions",
                                  f"-vara-report-outfile={ptfdd_report_name}",
                                  "-S", bc_path]

                opt_command = wrap_unlimit_stack_size(opt_command)
                opt_command = opt_command > f"{ptfdd_report_name}.log"

                with cleanup(prj_command):
                    exec_func_with_pe_error_handler(
                        opt_command,
                        create_default_analysis_failure_handler(
                            self.__experiment_handle,
                            self.project,
                            CoverageReport,
                            timeout_duration=TIMEOUT
                        )
                    )

        return actions.StepResult.OK


def get_feature_model_path(project: Project) -> Path:
    """Return the path to the feature model or raise an exception."""
    # FeatureModelProvider
    provider = FeatureModelProvider.create_provider_for_project(project)
    if provider is None:
        raise FeatureModelNotFound(project, None)

    path = provider.get_feature_model_path(project)

    if path is None or not path.exists():
        raise FeatureModelNotFound(project, path)
    return path


class GenerateCoverageExperiment(VersionExperiment, shorthand="GenCov"):
    """Generates empty report file."""

    NAME = "GenerateCoverage"

    REPORT_SPEC = ReportSpecification(CoverageReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        #project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g"]
        project.cflags += ["-O0", "-g"]

        # Activate source-based code coverage:
        # https://clang.llvm.org/docs/SourceBasedCodeCoverage.html
        project.cflags += ["-fprofile-instr-generate", "-fcoverage-mapping"]

        feature_model = get_feature_model_path(project).absolute()
        # Get clang to output bc files with feature annotations
        project.cflags += [
            "-fvara-feature",
            f"-fvara-fm-path={feature_model}",
        ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = (
            run.RuntimeExtension(project, self) << time.RunWithTime()
        )

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = (
            compiler.RunCompiler(project, self) << RunWLLVM() <<
            run.WithTimeout()
        )

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            Extract(
                project,
                BC_FILE_EXTENSIONS,
                handler=create_default_compiler_error_handler(
                    self.get_handle(),
                    project,
                    self.get_handle().report_spec().main_report,
                )
            )
        )

        # Only consider binaries with a workload
        for binary in project.binaries:
            workload_cmds = workload_commands(
                project, binary, [WorkloadCategory.EXAMPLE]
            )
            if not workload_cmds:
                continue
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report,
                project,
                binary,
                get_current_config_id(project),
            )

            analysis_actions.append(actions.Echo(result_filepath))
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath,
                    [
                        GenerateCoverage(
                            project, binary, workload_cmds, self.get_handle()
                        )
                    ],
                )
            )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

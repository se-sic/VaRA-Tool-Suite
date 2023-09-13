""""Coverage experiment."""

import json
import typing as tp
from copy import deepcopy
from pathlib import Path
from shutil import copy
from tempfile import TemporaryDirectory

from benchbuild import Project, watch
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmMem
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
    OutputFolderStep,
)
from varats.experiment.wllvm import RunWLLVM, BCFileExtensions, Extract
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


class SaveBCFiles(actions.ProjectStep):  # type: ignore[misc]
    """SaveBCFiles experiment."""

    NAME = "SaveBCFiles"
    DESCRIPTION = "Saves the BC files to a temporary directory."

    project: VProject

    def __init__(
        self,
        project: Project,
        tmpdir: TemporaryDirectory[str],
    ):
        super().__init__(project=project)
        self.tmpdir = tmpdir

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """Saves the BC files to a temporary directory."""
        for binary in self.project.binaries:
            bc_path = Path(self.project.source_of_primary) / f"{binary.path}.bc"
            copy(bc_path, self.tmpdir.name)

        return actions.StepResult.OK


class CleanupTmpdir(actions.ProjectStep):  # type: ignore[misc]
    """SaveBCFiles experiment."""

    NAME = "CleanupTmpdir"
    DESCRIPTION = "Calls cleanup on a tmpdir"

    project: VProject

    def __init__(
        self,
        project: Project,
        tmpdir: TemporaryDirectory[str],
    ):
        super().__init__(project=project)
        self.tmpdir = tmpdir

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        self.tmpdir.cleanup()

        return actions.StepResult.OK


class GenerateCoverage(OutputFolderStep):  # type: ignore[misc]
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
        feature_model: Path,
        bc_path: Path,
        _experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.binary = binary
        self.__workload_cmds = workload_cmds
        self.__experiment_handle = _experiment_handle
        self.__feature_model = feature_model
        self.__bc_path = bc_path

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:  # pylint: disable=too-many-locals
        """Runs project and export coverage information + bc files."""
        with local.cwd(self.project.builddir):
            if not self.__workload_cmds:
                # No workload to execute.
                # Fail because we don't get any coverage data
                return actions.StepResult.ERROR
            extra_args = get_extra_config_options(self.project)

            # Treat space in extra_args as seperate arguments
            seperated_extra_args = []
            for extra_arg in extra_args:
                seperated_extra_args.extend(extra_arg.split(' ', 1))

            profile_raw_names = []
            for prj_command in self.__workload_cmds:
                cmd = prj_command.command[seperated_extra_args]
                pb_cmd = cmd.as_plumbum(project=self.project)

                profile_raw_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.profraw"
                )
                profile_raw_names.append(profile_raw_name)
                run_cmd = watch(
                    pb_cmd.with_env(LLVM_PROFILE_FILE=profile_raw_name)
                )

                with cleanup(prj_command):
                    if self.binary.valid_exit_codes:
                        # Expect correct return code
                        run_cmd(retcode=self.binary.valid_exit_codes)
                    else:
                        run_cmd()

            # Merge all profraws to profdata file

            profdata_name = (
                tmp_dir / f"coverage_report-llvm-prof.{extra_args}.profdata"
            )
            json_name = tmp_dir / f"coverage_report-llvm-cov.{extra_args}.json"

            llvm_profdata = local["llvm-profdata"]
            llvm_cov = local["llvm-cov"]
            llvm_cov = llvm_cov["export", f"--instr-profile={profdata_name}",
                                Path(self.project.source_of_primary) /
                                self.binary.path]

            llvm_profdata("merge", *profile_raw_names, "-o", profdata_name)
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

            # Run Vara for analyzing binary

            ptfdd_report_name = tmp_dir / "coverage_report-vara_opt.ptfdd"
            bc_name = tmp_dir / "coverage_report-vara_opt.bc"
            copy(self.__bc_path, bc_name)

            # Copy FeatureModel.xml
            model_name = tmp_dir / "coverage_report-vara-feature_model.xml"
            copy(self.__feature_model, model_name)

            opt_command = opt["-enable-new-pm=0", "-vara-PTFDD",
                              "-vara-export-feature-dbg",
                              #"-vara-view-IRegions",
                              f"-vara-report-outfile={ptfdd_report_name}", "-S",
                              self.__bc_path]

            opt_command = wrap_unlimit_stack_size(opt_command)
            opt_command = opt_command > f"{ptfdd_report_name}.log"

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
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("20G")]

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

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

        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        #project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g"]
        project.cflags += ["-O0", "-g", "-fno-exceptions", "-fuse-ld=lld"]

        # Compile coverage instructions seperate. We don't want them in LLVM IR
        project_coverage = deepcopy(project)

        # Activate source-based code coverage:
        # https://clang.llvm.org/docs/SourceBasedCodeCoverage.html
        project_coverage.cflags += [
            "-fprofile-instr-generate", "-fcoverage-mapping"
        ]

        feature_model = get_feature_model_path(project).absolute()
        # Get clang to output bc files with feature annotations
        project.cflags += [
            "-fvara-feature",
            f"-fvara-fm-path={feature_model}",
        ]

        tmpdir = TemporaryDirectory()  # pylint: disable=consider-using-with

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
        analysis_actions.append(SaveBCFiles(project, tmpdir))
        analysis_actions.append(actions.Clean(project))

        project = project_coverage
        analysis_actions.append(actions.MakeBuildDir(project))
        analysis_actions.append(actions.ProjectEnvironment(project))
        analysis_actions.append(actions.Compile(project))

        # Only consider binaries with a workload
        for binary in project.binaries:
            workload_cmds = workload_commands(
                project,
                binary,
                [WorkloadCategory.JAN]  #[WorkloadCategory.JAN_2]
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
            bc_path = Path(tmpdir.name) / f"{binary.name}.bc"
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath,
                    [
                        GenerateCoverage(
                            project, binary, workload_cmds, feature_model,
                            bc_path, self.get_handle()
                        )
                    ],
                )
            )
        analysis_actions.append(CleanupTmpdir(project, tmpdir))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

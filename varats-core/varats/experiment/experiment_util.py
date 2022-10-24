"""Utility module for BenchBuild experiments."""

import os
import random
import shutil
import sys
import tempfile
import textwrap
import traceback
import typing as tp
from abc import abstractmethod
from pathlib import Path
from types import TracebackType

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable

from benchbuild import source
from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.utils.actions import Step, MultiStep, StepResult, run_any_child
from benchbuild.utils.cmd import prlimit, mkdir
from plumbum.commands import ProcessExecutionError

import varats.revision.revisions as revs
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import (
    BaseReport,
    FileStatusExtension,
    ReportFilepath,
    ReportSpecification,
    ReportFilename,
)
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg, bb_cfg

if tp.TYPE_CHECKING:
    TempDir = tempfile.TemporaryDirectory[str]
else:
    TempDir = tempfile.TemporaryDirectory


def get_varats_result_folder(project: Project) -> Path:
    """
    Get the project specific path to the varats result folder.

    Args:
        project: to lookup the result folder for

    Returns:
        path to the project specific result folder
    """
    result_folder_template = "{result_dir}/{project_dir}"

    vara_result_folder = result_folder_template.format(
        result_dir=str(bb_cfg()["varats"]["outfile"]),
        project_dir=str(project.name)
    )

    mkdir("-p", vara_result_folder)

    return Path(vara_result_folder)


class PEErrorHandler():
    """Error handler for process execution errors."""

    def __init__(
        self,
        result_folder: Path,
        error_file_name: str,
        timeout_duration: tp.Optional[str] = None,
        delete_files: tp.Optional[tp.List[Path]] = None
    ):
        self.__result_folder = result_folder
        self.__error_file_name = error_file_name
        self.__timeout_duration = timeout_duration
        self.__delete_files = delete_files

    def __call__(self, ex: Exception, func: tp.Callable[..., tp.Any]) -> None:
        if self.__delete_files is not None:
            for delete_file in self.__delete_files:
                try:
                    delete_file.unlink()
                except FileNotFoundError:
                    pass

        error_file = self.__result_folder / self.__error_file_name

        if not os.path.exists(self.__result_folder):
            os.makedirs(self.__result_folder, exist_ok=True)
        with open(error_file, 'w') as outfile:
            if isinstance(ex, ProcessExecutionError):
                if ex.retcode == 124:
                    timeout_duration = str(self.__timeout_duration)
                    extra_error = f"""Command:
{str(func)}
Timeout after: {timeout_duration}

"""
                    outfile.write(extra_error)
                    outfile.flush()

            outfile.write("-----\nTraceback:\n")
            traceback.print_exc(file=outfile)

        raise ex


class FunctionPEErrorWrapper():
    """
    Wrap a function call with an exception handler.

    Args:
        func: function to be executed
        handler: function to handle exception
    """

    def __init__(
        self, func: tp.Callable[..., tp.Any], handler: PEErrorHandler
    ) -> None:
        self.__func = func
        self.__handler = handler

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        try:
            return self.__func(*args, **kwargs)
        except Exception as ex:  # pylint: disable=broad-except
            self.__handler(ex, self.__func)
            return None


def exec_func_with_pe_error_handler(
    func: tp.Callable[..., tp.Any], handler: PEErrorHandler
) -> None:
    """
    Execute a function call with an exception handler.

    Args:
        func: function to be executed
        handler: function to handle exception
    """
    FunctionPEErrorWrapper(func, handler)()


def get_default_compile_error_wrapped(
    experiment_handle: 'ExperimentHandle', project: Project,
    report_type: tp.Type[BaseReport]
) -> FunctionPEErrorWrapper:
    """
    Setup the default project compile function with an error handler.

    Args:
        experiment_handle: handle to the current experiment
        project: that will be compiled
        report_type: that should be generated

    Returns:
        project compilation function, wrapped with automatic error handling
    """
    return FunctionPEErrorWrapper(
        project.compile,
        create_default_compiler_error_handler(
            experiment_handle, project, report_type
        )
    )


def create_default_compiler_error_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    binary: tp.Optional[ProjectBinaryWrapper] = None
) -> PEErrorHandler:
    """
    Create a default PEErrorHandler for compile errors, based on the `project`,
    `report_type`.

    Args:
        experiment_handle: handle to the current experiment
        project: currently under analysis
        report_type: that should be generated
        binary: if only a specific binary is handled

    Retruns: a initialized PEErrorHandler
    """
    return create_default_error_handler(
        experiment_handle, project, report_type,
        FileStatusExtension.COMPILE_ERROR, binary
    )


def create_default_analysis_failure_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    binary: tp.Optional[ProjectBinaryWrapper] = None,
    timeout_duration: tp.Optional[str] = None,
) -> PEErrorHandler:
    """
    Create a default PEErrorHandler for analysis failures, based on the
    `project`, `report_type`.

    Args:
        experiment_handle: handle to the current experiment
        project: currently under analysis
        report_type: that should be generated
        binary: if only a specific binary is handled
        timeout_duration: set timeout

    Retruns: a initialized PEErrorHandler
    """
    return create_default_error_handler(
        experiment_handle, project, report_type, FileStatusExtension.FAILED,
        binary, timeout_duration
    )


def create_default_error_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    error_type: FileStatusExtension,
    binary: tp.Optional[ProjectBinaryWrapper] = None,
    timeout_duration: tp.Optional[str] = None,
) -> PEErrorHandler:
    """
    Create a default PEErrorHandler based on the `project`, `report_type`.

    Args:
        experiment_handle: handle to the current experiment
        project: currently under analysis
        report_type: that should be generated
        error_type: a FSE describing the problem type
        timeout_duration: set timeout
        binary: if only a specific binary is handled

    Retruns: a initialized PEErrorHandler
    """
    error_output_folder = get_varats_result_folder(project)

    return PEErrorHandler(
        error_output_folder,
        str(
            experiment_handle.get_file_name(
                report_type.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name if binary else "all",
                project_revision=ShortCommitHash(project.version_of_primary),
                project_uuid=str(project.run_uuid),
                extension_type=error_type
            )
        ),
        timeout_duration=timeout_duration
    )


def wrap_unlimit_stack_size(cmd: tp.Callable[..., tp.Any]) -> tp.Any:
    """
    Wraps a command with prlimit to be executed with max stack size, i.e.,
    setting the soft limit to the hard limit.

    Args:
        cmd: command that should be executed with max stack size

    Returns: wrapped command
    """
    max_stacksize_16gb = 17179869184
    return prlimit[f"--stack={max_stacksize_16gb}:", cmd]


VersionType = tp.TypeVar('VersionType')


class ExperimentHandle():
    """Handle to an experiment that provides helper interfaces for analysis
    steps to utilize experiment specific data."""

    def __init__(self, experiment: 'VersionExperiment') -> None:
        self.__experiment = experiment

    def get_file_name(
        self,
        report_shorthand: str,
        project_name: str,
        binary_name: str,
        project_revision: ShortCommitHash,
        project_uuid: str,
        extension_type: FileStatusExtension,
        config_id: tp.Optional[int] = None
    ) -> ReportFilename:
        """
        Generates a filename for a report file that is generated by the
        experiment.

        Args:
            report_shorthand: unique shorthand for the report
            project_name: name of the project for which the
                          report was generated
            binary_name: name of the binary for which the report was generated
            project_revision: revision (commit hash)of the analyzed project
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report

        Returns:
            name for the report file that can later be uniquly identified
        """
        return self.__experiment.report_spec(
        ).get_report_type(report_shorthand).get_file_name(
            self.__experiment.shorthand(), project_name, binary_name,
            project_revision, project_uuid, extension_type, config_id
        )

    def report_spec(self) -> ReportSpecification:
        """Experiment report specification."""
        return self.__experiment.report_spec()


class VersionExperiment(Experiment):  # type: ignore
    """Base class for experiments that want to analyze different project
    revisions."""

    REPORT_SPEC: ReportSpecification
    SHORTHAND: str

    @classmethod
    def __init_subclass__(
        cls, shorthand: str, *args: tp.Any, **kwargs: tp.Any
    ) -> None:
        super().__init_subclass__(*args, **kwargs)

        cls.SHORTHAND = shorthand
        if not hasattr(cls, 'REPORT_SPEC'):
            raise AssertionError(
                f"{cls.__name__}@{cls.__module__} does not specify"
                " a REPORT_SPEC."
            )

    @classmethod
    def shorthand(cls) -> str:
        """Experiment shorthand."""
        return cls.SHORTHAND

    @classmethod
    def report_spec(cls) -> ReportSpecification:
        """Experiment report specification."""
        return cls.REPORT_SPEC

    @classmethod
    def file_belongs_to_experiment(cls, file_name: str) -> bool:
        """
        Checks if the file belongs to this experiment.

        Args:
            file_name: name of the file to check

        Returns:
            True, if the file belongs to this experiment type
        """
        try:
            other_short_hand = ReportFilename(file_name).experiment_shorthand
            return cls.shorthand() == other_short_hand
        except ValueError:
            return False

    def get_handle(self) -> ExperimentHandle:
        return ExperimentHandle(self)

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    @staticmethod
    def _sample_num_versions(
        versions: tp.List[VersionType]
    ) -> tp.List[VersionType]:
        if vara_cfg()["experiment"]["sample_limit"].value is None:
            return versions

        sample_size = int(vara_cfg()["experiment"]["sample_limit"])
        versions = [
            versions[i] for i in sorted(
                random.
                sample(range(len(versions)), min(sample_size, len(versions)))
            )
        ]
        return versions

    @classmethod
    def sample(cls,
               prj_cls: tp.Type[Project]) -> tp.List[source.VariantContext]:
        """
        Adapt version sampling process if needed, otherwise fallback to default
        implementation.

        Args:
            prj_cls: project class

        Returns:
            list of sampled versions
        """
        variants = list(source.product(*prj_cls.SOURCE))

        if bool(vara_cfg()["experiment"]["random_order"]):
            random.shuffle(variants)

        fs_blacklist = vara_cfg()["experiment"]["file_status_blacklist"].value
        fs_whitelist = vara_cfg()["experiment"]["file_status_whitelist"].value

        if fs_blacklist or fs_whitelist:
            fs_good = set(FileStatusExtension) if not fs_whitelist else set()

            fs_good -= {
                FileStatusExtension.get_file_status_from_str(x)
                for x in fs_blacklist
            }
            fs_good |= {
                FileStatusExtension.get_file_status_from_str(x)
                for x in fs_whitelist
            }

            report_specific_bad_revs = []
            for report_type in cls.report_spec():
                report_specific_bad_revs.append({
                    revision.hash
                    for revision, file_status in
                    # TODO (se-sic/VaRA#840): needs updated VariantContext handling
                    revs.get_tagged_revisions(prj_cls, cls, report_type).items()
                    if file_status[None] not in fs_good
                })

            bad_revisions = report_specific_bad_revs[0].intersection(
                *report_specific_bad_revs[1:]
            )

            variants = list(
                filter(lambda var: str(var[0]) not in bad_revisions, variants)
            )

        if not variants:
            print("Could not find any unprocessed variants.")
            return []

        variants = cls._sample_num_versions(variants)

        if bool(bb_cfg()["versions"]["full"]):
            return [source.context(*var) for var in variants]

        return [source.context(*variants[0])]


class ZippedReportFolder(TempDir):
    """
    Context manager for creating a folder report, i.e., a report file which is
    actually a folder containing multiple files and other folders.

    Example usage: An experiment step can, with this context manager, simply
    create a folder into which all kinds of data is dropped into. After the
    completion of the step (leaving the context manager), all files dropped into
    the folder will be compressed and stored as a single report.
    """

    def __init__(self, result_report_path: Path) -> None:
        super().__init__()
        self.__result_report_name: Path = result_report_path.with_suffix('')

    def __exit__(
        self, exc_type: tp.Optional[tp.Type[BaseException]],
        exc_value: tp.Optional[BaseException],
        exc_traceback: tp.Optional[TracebackType]
    ) -> None:
        # Don't create an empty zip archive.
        if os.listdir(self.name):
            shutil.make_archive(
                str(self.__result_report_name), "zip", Path(self.name)
            )

        super().__exit__(exc_type, exc_value, exc_traceback)


@runtime_checkable
class NeedsOutputFolder(Protocol):

    def __call__(self, tmp_folder: Path) -> StepResult:
        ...


def run_child_with_output_folder(
    child: NeedsOutputFolder, tmp_folder: Path
) -> StepResult:
    return child(tmp_folder)


class ZippedExperimentSteps(MultiStep):
    """Runs multiple actions, providing them a shared tmp folder that afterwards
    is zipped into an archive.."""

    NAME = "ZippedSteps"
    DESCRIPTION = "Run multiple actions with a shared tmp folder"

    def __init__(
        self, output_filepath: ReportFilepath,
        actions: tp.Optional[tp.List[NeedsOutputFolder]]
    ) -> None:
        super().__init__(actions)
        self.__output_filepath = output_filepath

    def __run_children(self, tmp_folder: Path) -> tp.List[StepResult]:
        results: tp.List[StepResult] = []

        for child in self.actions:
            results.append(
                run_child_with_output_folder(
                    tp.cast(NeedsOutputFolder, child), tmp_folder
                )
            )

        return results

    def __call__(self) -> StepResult:
        results: tp.List[StepResult] = []

        with ZippedReportFolder(self.__output_filepath.full_path()) as tmp_dir:
            results = self.__run_children(Path(tmp_dir))

        overall_step_result = max(results) if results else StepResult.OK
        if overall_step_result is not StepResult.OK:
            error_filepath = self.__output_filepath.with_status(
                FileStatusExtension.FAILED
            )
            self.__output_filepath.full_path().rename(
                error_filepath.full_path()
            )

        return overall_step_result

    def __str__(self, indent: int = 0) -> str:
        sub_actns = "\n".join([a.__str__(indent + 1) for a in self.actions])
        return textwrap.indent(
            f"\nZippedExperimentSteps:\n{sub_actns}", indent * " "
        )


def __create_new_result_filepath_impl(
    exp_handle: ExperimentHandle,
    report_type: tp.Type[BaseReport],
    project: VProject,
    binary: ProjectBinaryWrapper,
    extension_type: FileStatusExtension,
    config_id: tp.Optional[int] = None
) -> ReportFilepath:
    """
    Create a result filepath for the specified file extension and report of the
    executed experiment/project combination.

    Args:
        exp_handle: handle to the current experiment
        report_type: type of the report
        project: current project
        binary: current binary
        extension_type: of the report
        config_id: optional id to specify the used configuration

    Returns: formatted filepath
    """
    varats_result_folder = get_varats_result_folder(project)

    result_filepath = ReportFilepath(
        varats_result_folder,
        exp_handle.get_file_name(
            report_type.shorthand(),
            project_name=str(project.name),
            binary_name=binary.name,
            project_revision=ShortCommitHash(project.version_of_primary),
            project_uuid=str(project.run_uuid),
            extension_type=extension_type,
            config_id=config_id
        )
    )

    if config_id:
        # We need to ensure that the config folder is created in the
        # background, so configuration specific reports can be created.
        config_folder = result_filepath.full_path().parent
        config_folder.mkdir(parents=True, exist_ok=True)

    return result_filepath


def create_new_success_result_filepath(
    exp_handle: ExperimentHandle,
    report_type: tp.Type[BaseReport],
    project: VProject,
    binary: ProjectBinaryWrapper,
    config_id: tp.Optional[int] = None
) -> ReportFilepath:
    """
    Create a result filepath for a successfull report of the executed
    experiment/project combination.

    Args:
        exp_handle: handle to the current experiment
        report_type: type of the report
        project: current project
        binary: current binary
        config_id: optional id to specify the used configuration

    Returns: formatted success filepath
    """
    return __create_new_result_filepath_impl(
        exp_handle, report_type, project, binary, FileStatusExtension.SUCCESS,
        config_id
    )


def create_new_failed_result_filepath(
    exp_handle: ExperimentHandle,
    report_type: tp.Type[BaseReport],
    project: VProject,
    binary: ProjectBinaryWrapper,
    config_id: tp.Optional[int] = None
) -> ReportFilepath:
    """
    Create a result filepath for a failed report of the executed
    experiment/project combination.

    Args:
        exp_handle: handle to the current experiment
        report_type: type of the report
        project: current project
        binary: current binary
        config_id: optional id to specify the used configuration

    Returns: formatted fail filepath
    """
    return __create_new_result_filepath_impl(
        exp_handle, report_type, project, binary, FileStatusExtension.FAILED,
        config_id
    )

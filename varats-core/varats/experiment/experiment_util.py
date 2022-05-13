"""Utility module for BenchBuild experiments."""

import os
import random
import shutil
import tempfile
import traceback
import typing as tp
from abc import abstractmethod
from pathlib import Path
from types import TracebackType

from benchbuild import source
from benchbuild.experiment import Experiment
from benchbuild.project import Project
from benchbuild.utils.actions import Step
from benchbuild.utils.cmd import prlimit, mkdir
from plumbum.commands import ProcessExecutionError

from varats.project.project_util import ProjectBinaryWrapper
from varats.report.report import (
    BaseReport,
    FileStatusExtension,
    ReportSpecification,
    ReportFilename,
)
from varats.revision.revisions import get_tagged_revisions
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
            experiment_handle, project, report_type,
            get_varats_result_folder(project)
        )
    )


def create_default_compiler_error_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    output_folder: tp.Optional[Path] = None,
    binary: tp.Optional[ProjectBinaryWrapper] = None
) -> PEErrorHandler:
    """
    Create a default PEErrorHandler for compile errors, based on the `project`,
    `report_type`.

    Args:
        experiment_handle: handle to the current experiment
        project: currently under analysis
        report_type: that should be generated
        output_folder: where the errors will be placed
        binary: if only a specific binary is handled

    Retruns: a initialized PEErrorHandler
    """
    return create_default_error_handler(
        experiment_handle, project, report_type,
        FileStatusExtension.COMPILE_ERROR, output_folder, binary
    )


def create_default_analysis_failure_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    output_folder: tp.Optional[Path] = None,
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
        output_folder: where the errors will be placed
        binary: if only a specific binary is handled
        timeout_duration: set timeout

    Retruns: a initialized PEErrorHandler
    """
    return create_default_error_handler(
        experiment_handle, project, report_type, FileStatusExtension.FAILED,
        output_folder, binary, timeout_duration
    )


def create_default_error_handler(
    experiment_handle: 'ExperimentHandle',
    project: Project,
    report_type: tp.Type[BaseReport],
    error_type: FileStatusExtension,
    output_folder: tp.Optional[Path] = None,
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
        output_folder: where the errors will be placed
        timeout_duration: set timeout
        binary: if only a specific binary is handled

    Retruns: a initialized PEErrorHandler
    """
    error_output_folder = output_folder if output_folder else Path(
        f"{bb_cfg()['varats']['outfile']}/{project.name}"
    )

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
            project_revision, project_uuid, extension_type
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
                    revision.hash for revision, file_status in
                    get_tagged_experiment_specific_revisions(
                        prj_cls, report_type, experiment_type=cls
                    ) if file_status not in fs_good
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


def get_tagged_experiment_specific_revisions(
    project_cls: tp.Type[Project],
    result_file_type: tp.Type[BaseReport],
    tag_blocked: bool = True,
    experiment_type: tp.Optional[tp.Type[VersionExperiment]] = None
) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
    """
    Calculates a list of revisions of a project that belong to an experiment,
    tagged with the file status. If two files exists the newest is considered
    for detecting the status.

    Args:
        project_cls: target project
        result_file_type: the type of the result file
        tag_blocked: whether to tag blocked revisions as blocked
        experiment_type: target experiment type

    Returns:
        list of tuples (revision, ``FileStatusExtension``)
    """

    def experiment_filter(file_path: Path) -> bool:
        if experiment_type is None:
            return True

        return experiment_type.file_belongs_to_experiment(file_path.name)

    return get_tagged_revisions(
        project_cls, result_file_type, tag_blocked, experiment_filter
    )


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

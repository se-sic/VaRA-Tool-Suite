"""The Report module implements basic report functionalities and provides a
minimal interface ``BaseReport`` to implement own reports."""

import re
import shutil
import typing as tp
import weakref
from enum import Enum
from pathlib import Path, PosixPath
from tempfile import TemporaryDirectory
from types import TracebackType

from plumbum import colors
from plumbum.colorlib.styles import Color

from varats.utils.git_util import ShortCommitHash


class FileStatusExtension(Enum):
    """
    Enum to abstract the status of a file.

    Specific report files can map these to their own specific representation.
    """
    value: tp.Tuple[str, Color]  # pylint: disable=invalid-name

    SUCCESS = ("success", colors.green)
    INCOMPLETE = ("incomplete", colors.orangered1)
    FAILED = ("failed", colors.lightred)
    COMPILE_ERROR = ("cerror", colors.red)
    MISSING = ("###", colors.yellow3a)
    BLOCKED = ("blocked", colors.blue)

    def get_status_extension(self) -> str:
        """Returns the corresponding file ending to the status."""
        return str(self.value[0])

    def nice_name(self) -> str:
        """Returns a nicely formatted name."""
        if self == FileStatusExtension.COMPILE_ERROR:
            return "CompileError"

        return self.name.lower().capitalize()

    @property
    def status_color(self) -> Color:
        """Returns the corresponding color to the status."""
        return self.value[1]

    def get_colored_status(self) -> str:
        """Returns the corresponding file status, colored in the specific status
        color."""
        return tp.cast(str, self.status_color[self.nice_name()])

    def num_color_characters(self) -> int:
        """Returns the number of non printable color characters."""
        return len(self.status_color[''])

    @staticmethod
    def get_physical_file_statuses() -> tp.Set['FileStatusExtension']:
        """Returns the set of file status extensions that are associated with
        real result files."""
        return {
            FileStatusExtension.SUCCESS, FileStatusExtension.FAILED,
            FileStatusExtension.COMPILE_ERROR
        }

    @staticmethod
    def get_virtual_file_statuses() -> tp.Set['FileStatusExtension']:
        """Returns the set of file status extensions that are not associated
        with real result files."""
        return {FileStatusExtension.MISSING, FileStatusExtension.BLOCKED}

    @staticmethod
    def get_regex_grp() -> str:
        """Returns a regex group that can match all file stati."""
        regex_grp = r"(?P<status_ext>("
        for status in FileStatusExtension:
            regex_grp += fr"{status.get_status_extension()}" + '|'

        # Remove the '|' at the end
        regex_grp = regex_grp[:-1]
        regex_grp += "))"
        return regex_grp

    @staticmethod
    def get_file_status_from_str(status_name: str) -> 'FileStatusExtension':
        """
        Converts the name of a status extensions to the specific enum value.

        Args:
            status_name: name of the status extension

        Returns:
            FileStatusExtension enum with the specified name

        Test:
        >>> FileStatusExtension.get_file_status_from_str('success')
        <FileStatusExtension.SUCCESS: ('success', <ANSIStyle: Green>)>

        >>> FileStatusExtension.get_file_status_from_str('SUCCESS')
        <FileStatusExtension.SUCCESS: ('success', <ANSIStyle: Green>)>

        >>> FileStatusExtension.get_file_status_from_str('###')
        <FileStatusExtension.MISSING: ('###', <ANSIStyle: Full: Yellow3A>)>

        >>> FileStatusExtension.get_file_status_from_str('CompileError')
        <FileStatusExtension.COMPILE_ERROR: ('cerror', <ANSIStyle: Red>)>
        """
        for fs_enum in FileStatusExtension:
            if status_name.upper(
            ) == fs_enum.name or status_name == fs_enum.value[
                0] or status_name == fs_enum.nice_name():
                return fs_enum

        raise ValueError(f"Unknown file status extension name: {status_name}")

    @staticmethod
    def combine(
        lhs: 'FileStatusExtension', rhs: 'FileStatusExtension'
    ) -> 'FileStatusExtension':
        """
        Combines two FileStatusExtension into one.

        Should no specific combination rule apply, the lhs is used as a default.
        """
        if (
            lhs == FileStatusExtension.SUCCESS and
            rhs != FileStatusExtension.SUCCESS
        ) or (
            rhs == FileStatusExtension.SUCCESS and
            lhs != FileStatusExtension.SUCCESS
        ):
            return FileStatusExtension.INCOMPLETE
        return lhs


class ReportFilename():
    """ReportFilename wraps special semantics about our report filenames around
    strings and paths."""

    __RESULT_FILE_REGEX = re.compile(
        r"(?P<experiment_shorthand>.*)-" + r"(?P<report_shorthand>.*)-" +
        r"(?P<project_name>.*)-(?P<binary_name>.*)-" +
        r"(?P<file_commit_hash>.*)_(?P<UUID>[0-9a-fA-F\-]*)_" +
        FileStatusExtension.get_regex_grp() + r"?(?P<file_ext>\..*)?" + "$"
    )

    __RESULT_FILE_TEMPLATE = (
        "{experiment_shorthand}-" + "{report_shorthand}-" + "{project_name}-" +
        "{binary_name}-" + "{project_revision}_" + "{project_uuid}_" +
        "{status_ext}" + "{file_ext}"
    )

    def __init__(self, file_name: tp.Union[str, Path]) -> None:
        if isinstance(file_name, (Path, PosixPath)):
            self.__filename = file_name.name
        else:
            self.__filename = str(file_name)

    @property
    def filename(self) -> str:
        """Literal file name."""
        return self.__filename

    @property
    def binary_name(self) -> str:
        """Name of the analyzed binary."""
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return str(match.group("binary_name"))

        raise ValueError(f'File {self.filename} name was wrongly formatted.')

    def has_status_success(self) -> bool:
        """
        Checks if the file name is a (Success) result file.

        Returns:
            True, if the file name is for a success file
        """
        return ReportFilename.result_file_has_status(
            self.filename, FileStatusExtension.SUCCESS
        )

    def has_status_failed(self) -> bool:
        """
        Check if the file name is a (Failed) result file.

        Returns:
            True, if the file name is for a failed file
        """
        return ReportFilename.result_file_has_status(
            self.filename, FileStatusExtension.FAILED
        )

    def has_status_compileerror(self) -> bool:
        """
        Check if the filename is a (CompileError) result file.

        Returns:
            True, if the file name is for a compile error file
        """
        return ReportFilename.result_file_has_status(
            self.filename, FileStatusExtension.COMPILE_ERROR
        )

    def has_status_missing(self) -> bool:
        """
        Check if the filename is a (Missing) result file.

        Returns:
            True, if the file name is for a missing file
        """
        return ReportFilename.result_file_has_status(
            self.filename, FileStatusExtension.MISSING
        )

    def has_status_blocked(self) -> bool:
        """
        Check if the filename is a (Blocked) result file.

        Returns:
            True, if the file name is for a blocked file
        """
        return ReportFilename.result_file_has_status(
            self.filename, FileStatusExtension.BLOCKED
        )

    @staticmethod
    def result_file_has_status(
        file_name: str, extension_type: FileStatusExtension
    ) -> bool:
        """
        Check if the passed file name is of the expected file status.

        Args:
            file_name: name of the file to check
            extension_type: expected file status extension

        Returns:
            True, if the file name is for a file with the the specified
            ``extension_type``
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(file_name)
        if match:
            return match.group("status_ext") == (
                FileStatusExtension.get_status_extension(extension_type)
            )
        return False

    def is_result_file(self) -> bool:
        """
        Check if the file name is formatted like a result file.

        Returns:
            True, if the file name is correctly formatted
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        return match is not None

    @property
    def commit_hash(self) -> ShortCommitHash:
        """
        Commit hash of the result file.

        Returns:
            the commit hash from a result file name
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return ShortCommitHash(match.group("file_commit_hash"))

        raise ValueError(f'File {self.filename} name was wrongly formatted.')

    @property
    def experiment_shorthand(self) -> str:
        """
        Experiment shorthand of the result file.

        Returns:
            the experiment shorthand from a result file
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return match.group("experiment_shorthand")

        raise ValueError(f'File {self.filename} name was wrongly formatted.')

    @property
    def report_shorthand(self) -> str:
        """
        Report shorthand of the result file.

        Returns:
            the report shorthand from a result file
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return match.group("report_shorthand")

        raise ValueError(f'File {self.filename} name was wrongly formatted.')

    @property
    def file_status(self) -> FileStatusExtension:
        """
        Get the FileStatusExtension from a result file.

        Returns:
            the FileStatusExtension of the result file
        """
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return FileStatusExtension.get_file_status_from_str(
                match.group("status_ext")
            )

        raise ValueError('File {file_name} name was wrongly formatted.')

    @property
    def uuid(self) -> str:
        """Report UUID of the result file, genereated by BenchBuild during the
        experiment."""
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return match.group("UUID")

        raise ValueError(f'File {self.filename} name was wrongly formatted.')

    @staticmethod
    def get_file_name(
        experiment_shorthand: str,
        report_shorthand: str,
        project_name: str,
        binary_name: str,
        project_revision: ShortCommitHash,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> 'ReportFilename':
        """
        Generates a filename for a report file out the different parts.

        Args:
            experiment_shorthand: unique shorthand of the experiment
            report_shorthand: unique shorthand of the report
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_revision: revision of the project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        status_ext = FileStatusExtension.get_status_extension(extension_type)

        # Add the missing '.' if none was given by the report
        if file_ext and not file_ext.startswith("."):
            file_ext = "." + file_ext

        return ReportFilename(
            ReportFilename.__RESULT_FILE_TEMPLATE.format(
                experiment_shorthand=experiment_shorthand,
                report_shorthand=report_shorthand,
                project_name=project_name,
                binary_name=binary_name,
                project_revision=project_revision,
                project_uuid=project_uuid,
                status_ext=status_ext,
                file_ext=file_ext
            )
        )

    def __str__(self) -> str:
        return self.filename

    def __repr__(self) -> str:
        return self.filename


class BaseReport():
    """Report base class to add general report properties and helper
    functions."""

    REPORT_TYPES: tp.Dict[str, tp.Type['BaseReport']] = {}

    SHORTHAND: str
    FILE_TYPE: str

    def __init__(self, path: Path) -> None:
        self.__path = path
        self.__filename = ReportFilename(path)

    @classmethod
    def __init_subclass__(
        cls, shorthand: str, file_type: str, *args: tp.Any, **kwargs: tp.Any
    ) -> None:
        super().__init_subclass__(*args, **kwargs)

        cls.SHORTHAND = shorthand
        cls.FILE_TYPE = file_type

        name = cls.__name__
        if name not in cls.REPORT_TYPES:
            cls.REPORT_TYPES[name] = cls

    @staticmethod
    def lookup_report_type_from_file_name(
        file_name: str
    ) -> tp.Optional[tp.Type['BaseReport']]:
        """
        Looks-up the correct report class from a given `file_name`.

        Args:
            file_name: of the report file

        Returns:
            corresponding report class
        """
        try:
            shorthand = ReportFilename(file_name).report_shorthand
        except ValueError:
            # Return nothing if we cannot correctly identify a shothand for the
            # specified file name
            return None
        return BaseReport.lookup_report_type_by_shorthand(shorthand)

    @staticmethod
    def lookup_report_type_by_shorthand(
        shorthand: str
    ) -> tp.Optional[tp.Type['BaseReport']]:
        """
        Looks-up the correct report class from a given report `shorthand`.

        Args:
            shorthand: of the report file

        Returns:
            corresponding report class
        """
        try:
            for report_type in BaseReport.REPORT_TYPES.values():
                if getattr(report_type, "SHORTHAND") == shorthand:
                    return report_type
        except ValueError:
            return None

        return None

    @classmethod
    def get_file_name(
        cls,
        experiment_shorthand: str,
        project_name: str,
        binary_name: str,
        project_revision: ShortCommitHash,
        project_uuid: str,
        extension_type: FileStatusExtension,
    ) -> ReportFilename:
        """
        Generates a filename for a report file.

        Args:
            experiment_shorthand: unique shorthand of the experiment
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_revision: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report

        Returns:
            name for the report file that can later be uniquly identified
        """
        return ReportFilename.get_file_name(
            experiment_shorthand, cls.SHORTHAND, project_name, binary_name,
            project_revision, project_uuid, extension_type, cls.FILE_TYPE
        )

    @property
    def path(self) -> Path:
        """Path to the report file."""
        return self.__path

    @property
    def filename(self) -> ReportFilename:
        """Filename of the report."""
        return self.__filename

    @classmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""
        return cls.SHORTHAND

    @classmethod
    def file_type(cls) -> str:
        """File type of this report."""
        return cls.FILE_TYPE

    @classmethod
    def is_correct_report_type(cls, file_name: str) -> bool:
        """
        Check if the passed file belongs to this report type.

        Args:
            file_name: name of the file to check

        Returns:
            True, if the file belongs to this report type
        """
        try:
            short_hand = ReportFilename(file_name).report_shorthand
            return short_hand == cls.shorthand()
        except ValueError:
            return False


class ReportSpecification():
    """Groups together multiple report types into a specification that can be
    used, e.g., by experiments, to request multiple reports."""

    def __init__(self, *report_types: tp.Type[BaseReport]) -> None:
        self.__reports_types = list(report_types)

    @property
    def report_types(self) -> tp.List[tp.Type[BaseReport]]:
        """Report types in this report specification."""
        return list(self.__reports_types)

    @property
    def main_report(self) -> tp.Type[BaseReport]:
        """Main report of this specification."""
        return self.__reports_types[0]

    def in_spec(self, report_type: tp.Type[BaseReport]) -> bool:
        """Checks if a report type is specified in this spec."""
        return report_type in self.report_types

    def get_report_type(self, shorthand: str) -> tp.Type[BaseReport]:
        """
        Look up a report type by it's shorthand.

        Args:
            shorthand: notation for the report

        Returns:
            the report if, should it be part of this spec
        """
        report_type = BaseReport.lookup_report_type_by_shorthand(shorthand)

        if report_type and self.in_spec(report_type):
            return report_type

        raise LookupError(
            f"Report corresponding to {shorthand} was not specified."
        )

    def __contains__(self, report_type: tp.Type[BaseReport]) -> bool:
        return self.in_spec(report_type)

    def __iter__(self) -> tp.Iterator[tp.Type[BaseReport]]:
        return iter(self.report_types)


T = tp.TypeVar('T', bound=BaseReport)


class ReportAggregate(
    BaseReport, tp.Generic[T], shorthand="Agg", file_type="zip"
):
    """Parses multiple reports of the same type stored inside a zip file."""

    def __init__(self, path: Path, report_type: tp.Type[T]) -> None:
        super().__init__(path)

        # Create a temporary directory for extraction and register finalizer, which will clean it up.
        self.__tmpdir = TemporaryDirectory()
        # pylint: disable=R1732
        self.__finalizer = weakref.finalize(self, self.__tmpdir.cleanup)

        # Extract archive and parse reports.
        if self.path.exists():
            shutil.unpack_archive(self.path, self.__tmpdir.name)

        self.__reports = [
            report_type(file) for file in Path(self.__tmpdir.name).iterdir()
        ]

    def remove(self) -> None:
        self.__finalizer()

    @property
    def removed(self) -> bool:
        return not self.__finalizer.alive

    @property
    def reports(self) -> tp.List[T]:
        """Returns the list of parsed reports."""
        return self.__reports

"""The Report module implements basic report functionalities and provides a
minimal interface ``BaseReport`` to implement own reports."""

import re
import typing as tp
from abc import abstractmethod
from enum import Enum
from pathlib import Path, PosixPath

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
    FAILED = ("failed", colors.lightred)
    COMPILE_ERROR = ("cerror", colors.red)
    MISSING = ("###", colors.orange3)
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
            regex_grp += r"{status_ext}".format(
                status_ext=status.get_status_extension()
            ) + '|'

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
        <FileStatusExtension.MISSING: ('###', <ANSIStyle: Full: Orange3>)>

        >>> FileStatusExtension.get_file_status_from_str('CompileError')
        <FileStatusExtension.COMPILE_ERROR: ('cerror', <ANSIStyle: Red>)>
        """
        for fs_enum in FileStatusExtension:
            if status_name.upper(
            ) == fs_enum.name or status_name == fs_enum.value[
                0] or status_name == fs_enum.nice_name():
                return fs_enum

        raise ValueError(f"Unknown file status extension name: {status_name}")


class ReportFilename():
    """ReportFilename wraps special semantics about our report filenames around
    strings and paths."""

    __RESULT_FILE_REGEX = re.compile(
        r"(?P<project_shorthand>.*)-" +
        r"(?P<project_name>.*)-(?P<binary_name>.*)-" +
        r"(?P<file_commit_hash>.*)_(?P<UUID>[0-9a-fA-F\-]*)_" +
        FileStatusExtension.get_regex_grp() + r"?(?P<file_ext>\..*)?" + "$"
    )

    __RESULT_FILE_TEMPLATE = (
        "{shorthand}-" + "{project_name}-" + "{binary_name}-" +
        "{project_version}_" + "{project_uuid}_" + "{status_ext}" + "{file_ext}"
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
        Check if the file name is formated like a result file.

        Returns:
            True, if the file name is correctly formated
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

        raise ValueError(f'File {self.filename} name was wrongly formated.')

    @property
    def shorthand(self) -> str:
        """
        Report shorthand of the result file.

        Returns:
            the report shorthand from a result file
        """

        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return match.group("project_shorthand")

        raise ValueError(f'File {self.filename} name was wrongly formated.')

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

        raise ValueError('File {file_name} name was wrongly formated.')

    @property
    def uuid(self) -> str:
        """Report UUID of the result file, genereated by BenchBuild during the
        experiment."""
        match = ReportFilename.__RESULT_FILE_REGEX.search(self.filename)
        if match:
            return match.group("UUID")

        raise ValueError(f'File {self.filename} name was wrongly formated.')

    @staticmethod
    def get_file_name(
        report_shorthand: str,
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a report file out the different parts.

        Args:
            report_shorthand: unique shorthand of the report
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
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

        return ReportFilename.__RESULT_FILE_TEMPLATE.format(
            shorthand=report_shorthand,
            project_name=project_name,
            binary_name=binary_name,
            project_version=project_version,
            project_uuid=project_uuid,
            status_ext=status_ext,
            file_ext=file_ext
        )

    def __str__(self) -> str:
        return self.filename

    def __repr__(self) -> str:
        return self.filename


class BaseReport():
    """Report base class to add general report properties and helper
    functions."""

    REPORT_TYPES: tp.Dict[str, tp.Type['BaseReport']] = dict()

    def __init__(self, path: Path) -> None:
        self.__path = path
        self.__filename = ReportFilename(path)

    @classmethod
    def __init_subclass__(cls, *args: tp.Any, **kwargs: tp.Any) -> None:
        # mypy does not yet fully understand __init_subclass__()
        # https://github.com/python/mypy/issues/4660
        super().__init_subclass__(*args, **kwargs)  # type: ignore

        name = cls.__name__
        BaseReport.__check_required_vars(cls, name, ["SHORTHAND"])
        if name not in cls.REPORT_TYPES:
            cls.REPORT_TYPES[name] = cls

    @staticmethod
    def __check_required_vars(
        class_type: tp.Any, class_name: str, req_vars: tp.List[str]
    ) -> None:
        for var in req_vars:
            if not hasattr(class_type, var):
                raise NameError((
                    f"{class_name} does not define "
                    f"a static variable {var}."
                ))

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
            shorthand = ReportFilename(file_name).shorthand
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

    @staticmethod
    @abstractmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = ".txt"
    ) -> str:
        """
        Generates a filename for a report file.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """

    @property
    def path(self) -> Path:
        """Path to the report file."""
        return self.__path

    @property
    def filename(self) -> ReportFilename:
        """Filename of the report."""
        return self.__filename

    @classmethod
    @abstractmethod
    def shorthand(cls) -> str:
        """Shorthand for this report."""

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
            short_hand = ReportFilename(file_name).shorthand
            return short_hand == str(getattr(cls, "SHORTHAND"))
        except ValueError:
            return False


class ReportSpecification():
    """Groups together multiple report types into a specification that can be
    used, e.g., by experiments, to request multiple reports."""

    def __init__(self, *report_types: tp.Type[BaseReport]) -> None:
        if len(report_types) == 0:
            raise AssertionError(
                "ReportSpecification needs at least one report type."
            )
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

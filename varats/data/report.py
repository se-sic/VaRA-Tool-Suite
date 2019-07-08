"""
Report module.
"""

import typing as tp
from enum import Enum
import re

from plumbum import colors
from plumbum.colorlib.styles import Color

from varats.data import reports as __REPORTS__


class FileStatusExtension(Enum):
    """
    Enum to abstract the status of a file.
    Specific report files can map these to their own specific representation.
    """

    Success = ("yaml", colors.green)
    Failed = ("failed", colors.lightred)
    CompileError = ("cerror", colors.red)
    Missing = ("###", colors.orange3)

    def get_file_ending(self) -> str:
        """
        Returns the corresponding file ending to the status.
        """
        return str(self.value[0])

    @property
    def status_color(self) -> Color:
        """
        Returns the corresponding color to the status.
        """
        return self.value[1]

    def get_colored_status(self) -> str:
        """
        Returns the corresponding file status, colored
        in the specific status color.
        """
        return tp.cast(str, self.status_color[self.name])

    @staticmethod
    def get_file_status(file_ending: str) -> 'FileStatusExtension':
        for status in FileStatusExtension:
            if str(status.value[0]) == file_ending:
                return status
        raise ValueError(
            'Unknown file ending {ending}'.format(ending=file_ending))

    @staticmethod
    def get_regex_grp() -> str:
        """
        Returns a regex group that can match all file stati.
        """
        regex_grp = r"(?P<EXT>("
        for status in FileStatusExtension:
            regex_grp += r"{file_ending}|".format(
                file_ending=status.get_file_ending())

        regex_grp = regex_grp[:-1]
        regex_grp += "))"
        return regex_grp


class MetaReport(type):

    REPORT_TYPES: tp.Dict[str, 'MetaReport'] = dict()

    __FILE_NAME_REGEX = re.compile(
        r"(?P<project_shorthand>.*)-" +
        r"(?P<project_name>.*)-(?P<binary_name>.*)-" +
        r"(?P<file_commit_hash>.*)_(?P<UUID>[0-9a-fA-F\-]*)\." +
        FileStatusExtension.get_regex_grp() + "$")

    __RESULT_FILE_TEMPLATE = (
        "{shorthand}-" + "{project_name}-" + "{binary_name}-" +
        "{project_version}_" + "{project_uuid}." + "{ext}")

    def __init__(cls: tp.Any, name: str, bases: tp.Tuple[tp.Any],
                 attrs: tp.Dict[str, tp.Any]) -> None:
        super(MetaReport, cls).__init__(name, bases, attrs)
        MetaReport.__check_accessor_methods(cls)

        if name != 'BaseReport':
            MetaReport.__check_required_vars(cls, name, ["SHORTHAND"])
            if name not in cls.REPORT_TYPES:
                cls.REPORT_TYPES[name] = cls

    def __check_accessor_methods(cls: tp.Any) -> None:
        """
        Check if all static accessor methods like `is_result_file_*` for every
        FileStatusExtension enum exist.

        For example: Report.is_result_file_success("file/path")
        """
        for file_status in FileStatusExtension:
            method_name = 'is_result_file_' + file_status.name.lower()
            if not hasattr(cls, method_name):
                raise NotImplementedError(
                    "Missing file accesser method {method_name}".format(
                        method_name=method_name))

    @staticmethod
    def is_result_file_success(file_name: str) -> bool:
        """ Check if the passed file name is a (Success) result file. """
        return MetaReport.is_result_file_status(file_name,
                                                FileStatusExtension.Success)

    @staticmethod
    def is_result_file_failed(file_name: str) -> bool:
        """ Check if the passed file name is a (Failed) result file. """
        return MetaReport.is_result_file_status(file_name,
                                                FileStatusExtension.Failed)

    @staticmethod
    def is_result_file_compileerror(file_name: str) -> bool:
        """ Check if the passed file name is a (Failed) result file. """
        return MetaReport.is_result_file_status(
            file_name, FileStatusExtension.CompileError)

    @staticmethod
    def is_result_file_missing(file_name: str) -> bool:
        """ Check if the passed file name is a (Missing) result file. """
        return MetaReport.is_result_file_status(file_name,
                                                FileStatusExtension.Missing)

    def __check_required_vars(cls: tp.Any, name: str,
                              req_vars: tp.List[str]) -> None:
        for var in req_vars:
            if not hasattr(cls, var):
                raise NameError(("{class_name} does not define "
                                 "a static variable {var_name}.").format(
                                     class_name=name, var_name=var))

    @staticmethod
    def is_result_file(file_name: str) -> bool:
        """ Check if the passed file name is a result file. """
        match = MetaReport.__FILE_NAME_REGEX.search(file_name)
        return match is not None

    @staticmethod
    def is_result_file_status(file_name: str,
                              extension_type: FileStatusExtension) -> bool:
        """ Check if the passed file name is a (failed) result file. """
        match = MetaReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return match.group("EXT") == (
                FileStatusExtension.get_file_ending(extension_type))
        return False

    @staticmethod
    def get_commit_hash_from_result_file(file_name: str) -> str:
        """ Get the commit hash from a result file name. """
        match = MetaReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return match.group("file_commit_hash")

        raise ValueError('File {file_name} name was wrongly formated.'.format(
            file_name=file_name))

    @staticmethod
    def get_status_from_result_file(file_name: str) -> FileStatusExtension:
        """ Get the FileStatusExtension from a result file name. """
        match = MetaReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return FileStatusExtension.get_file_status(match.group("EXT"))

        raise ValueError('File {file_name} name was wrongly formated.'.format(
            file_name=file_name))

    @staticmethod
    def get_file_name(report_shorthand: str, project_name: str,
                      binary_name: str, project_version: str,
                      project_uuid: str,
                      extension_type: FileStatusExtension) -> str:
        """
        Generates a filename for a commit report
        """
        ext = FileStatusExtension.get_file_ending(extension_type)

        return MetaReport.__RESULT_FILE_TEMPLATE.format(
            shorthand=report_shorthand,
            project_name=project_name,
            binary_name=binary_name,
            project_version=project_version,
            project_uuid=project_uuid,
            ext=ext)

    def is_correct_report_type(cls, file_name: str) -> bool:
        """ Check if the passed file belongs to this report type. """
        match = MetaReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return match.group("project_shorthand") == str(
                getattr(cls, "SHORTHAND"))
        return False


class BaseReport(metaclass=MetaReport):
    pass


# Discover and initialize all Reports
__REPORTS__.discover()

"""
Utility module for working with workloads.

Provides generic workload categories and helper functions to load, run, and
process different workloads.
"""
import itertools
import re
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild.command import (
    ArgsToken,
    PathToken,
    ProjectCommand,
    unwrap,
    filter_workload_index,
    WorkloadSet,
    Command,
)

from varats.base.configuration import PlainCommandlineConfiguration
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_command import VProjectCommand
from varats.project.varats_project import VProject
from varats.report.report import KeyedReportAggregate, ReportTy
from varats.utils.config import get_config, get_extra_config_options
from varats.utils.exceptions import auto_unwrap


class WorkloadCategory(Enum):
    """Collection of different workload categories, used for grouping workloads
    together."""
    value: int  # pylint: disable=invalid-name

    EXAMPLE = 0
    SMALL = 1
    MEDIUM = 2
    LARGE = 3
    JAN = 4
    JAN_2 = 5

    def __str__(self) -> str:
        return self.name.lower()


class RevisionBinaryRenderer:

    def __init__(self, binary_name: str) -> None:
        self.__binary_name = binary_name

    def unrendered(self) -> str:
        return f"<binaryLocFor({self.__binary_name})>"

    def rendered(self, project: VProject, **kwargs: tp.Any) -> Path:
        for binary in project.binaries:
            if binary.name == self.__binary_name:
                entry_point = binary.entry_point
                if entry_point:
                    return entry_point

        raise AssertionError(
            "Specified binary was not present in the current version."
        )


def specify_binary(binary_name: str) -> PathToken:
    return PathToken.make_token(RevisionBinaryRenderer(binary_name))


RSBinary = specify_binary


class ConfigurationParameterRenderer:

    def __init__(self, *default_args: str) -> None:
        self.__default_args = default_args

    def unrendered(self) -> str:
        return f"<params>"

    def rendered(self, project: VProject,
                 **kwargs: tp.Any) -> tp.Tuple[str, ...]:
        if get_config(project, PlainCommandlineConfiguration) is None:
            return self.__default_args
        return tuple(get_extra_config_options(project))


def specify_configuration_parameters(*default_args: str) -> ArgsToken:
    return ArgsToken.make_token(ConfigurationParameterRenderer(*default_args))


ConfigParams = specify_configuration_parameters


def workload_commands(
    project: VProject, binary: ProjectBinaryWrapper,
    requested_workload_tags: tp.List[WorkloadCategory]
) -> tp.List[ProjectCommand]:
    """
    Generates a list of project commands for a project and the specified
    workload sets.

    Args:
        project: the project to select the workloads from
        requested_workload_tags: optional list of workload tags

    Returns: list of project commands to execute the workloads
    """
    run_only: tp.Optional[WorkloadSet] = None
    if requested_workload_tags:
        run_only = WorkloadSet(*requested_workload_tags)

    project_cmds: tp.List[VProjectCommand] = [
        VProjectCommand(project, workload_cmd)
        for workload_cmd in itertools.chain(
            *
            filter_workload_index(run_only, unwrap(project.workloads, project))
        )
    ]

    return [
        cmd for cmd in project_cmds
        if cmd.path.name == binary.name and cmd.can_be_executed()
    ]


def create_workload_specific_filename(
    filename_base: str,
    cmd: Command,
    repetition: int = 0,
    file_suffix: str = ".txt"
) -> Path:
    if '_' in cmd.label:
        raise AssertionError(
            "Workload/Command labels must not contain underscores '_'!"
        )
    return Path(f"{filename_base}_{cmd.label}_{repetition}{file_suffix}")


__WORKLOAD_FILE_REGEX = re.compile(r".*\_(?P<label>.+)\_\d+$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    if (
        match :=
        __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    ):
        return str(match.group("label"))

    return None


class WorkloadSpecificReportAggregate(
    KeyedReportAggregate[str, ReportTy],
    tp.Generic[ReportTy],
    shorthand="",
    file_type=""
):

    def __init__(
        self,
        path: Path,
        report_type: tp.Type[ReportTy],
        label_method: tp.Callable[[Path], tp.Optional[str]] = get_workload_label
    ) -> None:
        super().__init__(
            path, report_type,
            auto_unwrap(
                "Files contained in a WorkloadSpecificReportAggregate should"
                "always be formatted correctly by the"
                "create_workload_specific_filename function."
            )(label_method)
        )

    def workload_names(self) -> tp.Collection[str]:
        return self.keys()

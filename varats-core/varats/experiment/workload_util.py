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
    Command,
    PathToken,
    ProjectCommand,
    WorkloadSet,
    filter_workload_index,
    unwrap,
)

from varats.base.configuration import PlainCommandlineConfiguration
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_command import VProjectCommand
from varats.project.varats_project import VProject
from varats.report.report import KeyedReportAggregate, ReportTy
from varats.utils.config import get_config, get_extra_config_options
from varats.utils.exceptions import auto_unwrap


class WorkloadCategory(Enum):
    """Collection of workload categories, used for grouping workloads."""

    value: int  # pylint: disable=invalid-name

    EXAMPLE = 0
    SMALL = 1
    MEDIUM = 2
    LARGE = 3

    def __str__(self) -> str:
        """Lowercase name of the category."""
        return self.name.lower()


class RevisionBinaryRenderer:
    """Renders the entry point of a binary in the current project revision."""

    def __init__(self, binary_name: str) -> None:
        """
        Initialize the renderer.

        Args:
            binary_name: name of the binary to render the entry point for
        """
        self.__binary_name = binary_name

    def unrendered(self) -> str:
        """Placeholder representation of the token."""
        return f"<binaryLocFor({self.__binary_name})>"

    def rendered(self, project: VProject, **kwargs: tp.Any) -> Path:  # ruff: ignore[unused-method-argument]
        """Entry point of the binary in the current revision of ``project``."""
        for binary in project.binaries:
            if binary.name == self.__binary_name:
                entry_point = binary.entry_point
                if entry_point:
                    return entry_point

        raise AssertionError(
            "Specified binary was not present in the current version."
        )


def specify_binary(binary_name: str) -> PathToken:
    """Create a token that renders to the entry point of ``binary_name``."""
    return PathToken.make_token(RevisionBinaryRenderer(binary_name))


RSBinary = specify_binary


class ConfigurationParameterRenderer:
    """Renders the command line parameters of the current configuration."""

    def __init__(self, *default_args: str) -> None:
        """
        Initialize the renderer.

        Args:
            default_args: arguments used if the project is not configured
        """
        self.__default_args = default_args

    def unrendered(self) -> str:  # ruff: ignore[no-self-use]
        """Placeholder representation of the token."""
        return "<params>"

    def rendered(self, project: VProject, **kwargs: tp.Any) -> tuple[str, ...]:  # ruff: ignore[unused-method-argument]
        """Command line parameters of the current configuration."""
        if get_config(project, PlainCommandlineConfiguration) is None:
            return self.__default_args
        return tuple(
            arg
            for option in get_extra_config_options(project)
            for arg in option.split()
        )


def specify_configuration_parameters(*default_args: str) -> ArgsToken:
    """Create a token that renders to the configuration parameters."""
    return ArgsToken.make_token(ConfigurationParameterRenderer(*default_args))


ConfigParams = specify_configuration_parameters


def workload_commands(
    project: VProject,
    binary: ProjectBinaryWrapper,
    requested_workload_tags: list[WorkloadCategory],
) -> list[ProjectCommand]:
    """
    Generates a list of project commands for a project and workload sets.

    Args:
        project: the project to select the workloads from
        binary: the binary whose workloads should be selected
        requested_workload_tags: optional list of workload tags

    Returns: list of project commands to execute the workloads
    """
    run_only: WorkloadSet | None = None
    if requested_workload_tags:
        run_only = WorkloadSet(*requested_workload_tags)

    project_cmds: list[VProjectCommand] = [
        VProjectCommand(project, workload_cmd)
        for workload_cmd in itertools.chain(
            *filter_workload_index(run_only, unwrap(project.workloads, project))
        )
    ]

    return [
        cmd
        for cmd in project_cmds
        if cmd.path.name == binary.path.name and cmd.can_be_executed()
    ]


def create_workload_specific_filename(
    filename_base: str,
    cmd: Command,
    repetition: int = 0,
    file_suffix: str = ".txt",
) -> Path:
    """
    Create a filename that encodes the workload label of ``cmd``.

    Args:
        filename_base: prefix of the filename
        cmd: command whose label is encoded in the filename
        repetition: repetition number
        file_suffix: suffix of the filename

    Returns:
        the workload-specific filename
    """
    if '_' in cmd.label:
        raise AssertionError(
            "Workload/Command labels must not contain underscores '_'!"
        )
    return Path(f"{filename_base}_{cmd.label}_{repetition}{file_suffix}")


__WORKLOAD_FILE_REGEX = re.compile(r".*\_(?P<label>.+)\_\d+(\.?\w*)?$")


def get_workload_label(workload_specific_report_file: Path) -> str | None:
    """Extract the workload label from a workload-specific filename."""
    if match := __WORKLOAD_FILE_REGEX.search(
        workload_specific_report_file.name
    ):
        return str(match.group("label"))

    return None


class WorkloadSpecificReportAggregate(
    KeyedReportAggregate[str, ReportTy],
    tp.Generic[ReportTy],
    shorthand="",
    file_type="",
):
    """Report aggregate whose reports are keyed by workload label."""

    def __init__(
        self,
        path: Path,
        report_type: type[ReportTy],
        label_method: tp.Callable[[Path], str | None] = get_workload_label,
    ) -> None:
        """
        Initialize the aggregate.

        Args:
            path: path to the aggregate report
            report_type: type of the contained reports
            label_method: extracts the workload label from a report filename
        """
        super().__init__(
            path,
            report_type,
            auto_unwrap(
                "Files contained in a WorkloadSpecificReportAggregate should"
                "always be formatted correctly by the "
                "create_workload_specific_filename function."
            )(label_method),
        )

    def workload_names(self) -> tp.Collection[str]:
        """Labels of all workloads contained in the aggregate."""
        return self.keys()

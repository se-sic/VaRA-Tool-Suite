"""
Utility module for working with workloads.

Provides generic workload categories and helper functions to load, run, and
process different workloads.
"""
import itertools
import typing as tp
from enum import Enum
from pathlib import Path

from benchbuild.command import (
    PathToken,
    ProjectCommand,
    unwrap,
    filter_workload_index,
    WorkloadSet,
    Command,
)

from varats.project.varats_project import VProject


class WorkloadCategory(Enum):
    """Collection of different workload categories, used for grouping workloads
    together."""
    value: int  # pylint: disable=invalid-name

    SMALL = 1
    MEDIUM = 2
    LARGE = 3

    def __str__(self) -> str:
        return self.name.lower()


class RevisionBinaryRenderer:

    def __init__(self, binary_name: str) -> None:
        self.__binary_name = binary_name

    def __call__(self, project: VProject, **kwargs: tp.Any) -> Path:
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


def workload_commands(
    project: VProject, *requested_workload_tags: WorkloadSet
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

    return [
        ProjectCommand(project, workload) for workload in itertools.chain(
            *
            filter_workload_index(run_only, unwrap(project.workloads, project))
        )
    ]


def create_workload_specific_filename(
    filename_base: str,
    cmd: Command,
    repetition: int = 0,
    file_suffix: str = ".txt"
) -> Path:
    return Path(f"{filename_base}_{cmd.label}_{repetition}{file_suffix}")

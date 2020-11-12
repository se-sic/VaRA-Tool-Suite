"""Module for writing bug-data metrics tables."""
import typing as tp
from pathlib import Path

from benchbuild.project import Project

from varats.provider.bug.bug_provider import BugProvider
from varats.tables.table import Table


class BugOverviewTable(Table):
    """Visualizes bug metrics of a project."""

    NAME = "b_bug_overview"

    def __init__(self, project: tp.Type[Project], **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

        with BugProvider.create_provider_for_project(project) as provider:
            if provider:
                self.__provider = provider
            else:
                self.__provider = BugProvider.create_default_provider(project)

    def tabulate(self) -> str:
        pass

    def save(
        self,
        path: tp.Optional[Path] = None,
    ) -> None:
        pass

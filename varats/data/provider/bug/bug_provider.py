"""Module for the :class:`BugProvider`."""
import logging
import re
import typing as tp
from collections import defaultdict

from benchbuild.project import Project
from github import Github
from github.Repository import Repository

import varats.data.provider.bug.bug as bug
from varats.data.provider.provider import Provider

LOG = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(r"https://github\.com/(.*)/(.*)\.git")


class BugProvider(Provider):
    """Provides bug information for a project."""

    def __init__(
        self, project: tp.Type[Project], github_project_name: tp.Optional[str]
    ) -> None:
        super().__init__(project)
        self.__github_project_name = github_project_name

    @classmethod
    def create_provider_for_project(
        cls, project: tp.Type[Project]
    ) -> tp.Optional['BugProvider']:
        match = GITHUB_URL_PATTERN.match(project.repository)
        if match:
            return BugProvider(project, f"{match.group(1)}/{match.group(2)}")
        return None

    @classmethod
    def create_default_provider(
        cls, project: tp.Type[Project]
    ) -> 'BugProvider':
        return BugDefaultProvider(project)

    def find_all_pygit_bugs(self) -> tp.FrozenSet[bug.PygitBug]:
        """
        Creates a set for all bugs of the provider's project.

        Returns:
            A set of PygitBugs.
        """
        if self.__github_project_name:
            return bug.find_all_pygit_bugs(self.__github_project_name)
        return frozenset()

    def find_all_raw_bugs(self) -> tp.FrozenSet[bug.RawBug]:
        """
        Creates a set for all bugs of the provider's project.

        Returns:
            A set of RawBugs.
        """
        if self.__github_project_name:
            return bug.find_all_raw_bugs(self.__github_project_name)
        return frozenset()

    def find_pygit_bug_by_fix(self,
                              fixing_commit: str) -> tp.FrozenSet[bug.PygitBug]:
        """
        Find the bug associated to some fixing commit in the provider's project,
        if there is any.

        Args:
            fixing_commit: Commit Hash of the potentially fixing commit

        Returns:
            A set of PygitBugs fixed by fixing_commit
        """
        if self.__github_project_name:
            return bug.find_pygit_bug_by_fix(
                self.__github_project_name, fixing_commit
            )
        return frozenset()

    def find_raw_bug_by_fix(self,
                            fixing_commit: str) -> tp.FrozenSet[bug.RawBug]:
        """
        Find the bug associated to some fixing commit in the provider's project,
        if there is any.

        Args:
            fixing_commit: Commit Hash of the potentially fixing commit

        Returns:
            A set of RawBugs fixed by fixing_commit
        """
        if self.__github_project_name:
            return bug.find_raw_bug_by_fix(
                self.__github_project_name, fixing_commit
            )
        return frozenset()

    def find_pygit_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.PygitBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain commit
        to the provider's project.

        Args:
            introducing_commit: Commit Hash of the introducing commit to look for

        Returns:
            A set of PygitBugs introduced by introducing_commit
        """
        if self.__github_project_name:
            return bug.find_pygit_bug_by_introduction(
                self.__github_project_name, introducing_commit
            )
        return frozenset()

    def find_raw_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.RawBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain
        commit.

        Args:
            introducing_commit: Commit Hash of the introducing commit to look for

        Returns:
            A set of RawBugs introduced by introducing_commit
        """
        if self.__github_project_name:
            return bug.find_raw_bug_by_introduction(
                self.__github_project_name, introducing_commit
            )
        return frozenset()


class BugDefaultProvider(BugProvider):
    """Default implementation of the :class:`Bug provider` for projects that do
    not (yet) support bugs."""

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(BugProvider, self).__init__(project)

    def find_all_pygit_bugs(self) -> tp.FrozenSet[bug.PygitBug]:
        return frozenset()

    def find_all_raw_bugs(self) -> tp.FrozenSet[bug.RawBug]:
        return frozenset()

    def find_pygit_bug_by_fix(self,
                              fixing_commit: str) -> tp.FrozenSet[bug.PygitBug]:
        return frozenset()

    def find_raw_bug_by_fix(self,
                            fixing_commit: str) -> tp.FrozenSet[bug.RawBug]:
        return frozenset()

    def find_pygit_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.PygitBug]:
        return frozenset()

    def find_raw_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.RawBug]:
        return frozenset()

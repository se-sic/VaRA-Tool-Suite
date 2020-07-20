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

        :return:
            A set of PygitBug Objects.
        """
        if self.__github_project_name:
            return bug.find_all_pygit_bugs(self.__github_project_name)
        return frozenset()

    def find_all_raw_bugs(self) -> tp.FrozenSet[bug.RawBug]:
        """
        Creates a set for all bugs of the provider's project.

        :return:
            A set of RawBug Objects.
        """
        if self.__github_project_name:
            return bug.find_all_raw_bugs(self.__github_project_name)
        return frozenset()

    def find_pygit_bug_by_fix(self,
                              fixing_commit: str) -> tp.Optional[bug.PygitBug]:
        """
        Find the bug associated to some fixing commit in the provider's project,
        if there is any.

        :param fixing_commit:
            Commit Hash of the potentially fixing commit
        :return:
            A PygitBug Object, if there is such a bug
            None, if there is no such bug
        """
        if self.__github_project_name:
            return bug.find_pygit_bug_by_fix(
                self.__github_project_name, fixing_commit
            )
        return None

    def find_raw_bug_by_fix(self,
                            fixing_commit: str) -> tp.Optional[bug.RawBug]:
        """
        Find the bug associated to some fixing commit in the provider's project,
        if there is any.

        :param fixing_commit:
            Commit Hash of the potentially fixing commit
        :return:
            A RawBug Object, if there is such a bug
            None, if there is no such bug
        """
        if self.__github_project_name:
            return bug.find_raw_bug_by_fix(
                self.__github_project_name, fixing_commit
            )
        return None

    def find_pygit_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.List[bug.PygitBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain commit
        to the provider's project.

        :param introducing_commit:
            Commit Hash of the introducing commit to look for
        :return:
            A list of PygitBug Objects
        """
        if self.__github_project_name:
            return bug.find_pygit_bug_by_introduction(
                self.__github_project_name, introducing_commit
            )
        return []

    def find_raw_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.List[bug.RawBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain
        commit.

        :param introducing_commit:
            Commit Hash of the introducing commit to look for
        :return:
            A list of RawBug Objects
        """
        if self.__github_project_name:
            return bug.find_raw_bug_by_introduction(
                self.__github_project_name, introducing_commit
            )
        return []


class BugDefaultProvider(BugProvider):
    """Default implementation of the :class:`Bug provider` for projects that do
    not (yet) support bugs."""

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(BugProvider, self).__init__(project)

    def find_all_pygit_bugs(self) -> tp.FrozenSet[bug.PygitBug]:
        return frozenset(set())

    def find_all_raw_bugs(self) -> tp.FrozenSet[bug.RawBug]:
        return frozenset(set())

    def find_pygit_bug_by_fix(self,
                              fixing_commit: str) -> tp.Optional[bug.PygitBug]:
        return None

    def find_raw_bug_by_fix(self,
                            fixing_commit: str) -> tp.Optional[bug.RawBug]:
        return None

    def find_pygit_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.List[bug.PygitBug]:
        return []

    def find_raw_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.List[bug.RawBug]:
        return []

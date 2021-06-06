"""Module for the :class:`BugProvider`."""
import logging
import typing as tp

from benchbuild.project import Project

import varats.provider.bug.bug as bug
from varats.project.project_util import (
    get_primary_project_source,
    is_git_source,
)
from varats.provider.provider import Provider
from varats.utils.github_util import get_github_repo_name_for_project

LOG = logging.getLogger(__name__)


def _union_commit_message_and_issue_event_pygit_bugs(
    issue_event_bugs: tp.FrozenSet[bug.PygitBug],
    commit_message_bugs: tp.FrozenSet[bug.PygitBug]
) -> tp.FrozenSet[bug.PygitBug]:
    """
    Customized unionizing of bug sets of commit message and issue event origin.
    Commit message bugs only get added if there is no issue event bug with the
    same fixing commit.

    Args:
        issue_event_bugs: The set of bugs originating from issue events.
        commit_message_bugs: The set of bugs originating from commit messages.

    Returns:
        The resulting set of all bugs.
    """
    resulting_bugs: tp.Set[bug.PygitBug] = set()
    for issue_event_bug in issue_event_bugs:
        resulting_bugs.add(issue_event_bug)

    for commit_message_bug in commit_message_bugs:
        if commit_message_bug.fixing_commit.hex not in {
            issue_event_bug.fixing_commit.hex
            for issue_event_bug in issue_event_bugs
        }:
            resulting_bugs.add(commit_message_bug)

    return frozenset(resulting_bugs)


def _union_commit_message_and_issue_event_raw_bugs(
    issue_event_bugs: tp.FrozenSet[bug.RawBug],
    commit_message_bugs: tp.FrozenSet[bug.RawBug]
) -> tp.FrozenSet[bug.RawBug]:
    """
    Customized unionizing of bug sets of commit message and issue event origin.
    Commit message bugs only get added if there is no issue event bug with the
    same fixing commit.

    Args:
        issue_event_bugs: The set of bugs originating from issue events.
        commit_message_bugs: The set of bugs originating from commit messages.

    Returns:
        The resulting set of all bugs.
    """
    resulting_bugs: tp.Set[bug.RawBug] = set()
    for issue_event_bug in issue_event_bugs:
        resulting_bugs.add(issue_event_bug)

    for commit_message_bug in commit_message_bugs:
        if commit_message_bug.fixing_commit not in {
            issue_event_bug.fixing_commit
            for issue_event_bug in issue_event_bugs
        }:
            resulting_bugs.add(commit_message_bug)

    return frozenset(resulting_bugs)


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
        primary_source = get_primary_project_source(project.NAME)

        if is_git_source(primary_source):
            # If project has Github repo, pass name as second arg, None ow.
            return BugProvider(
                project, get_github_repo_name_for_project(project)
            )
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
            issue_event_bugs = bug.find_all_issue_pygit_bugs(self.project.NAME)
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_all_commit_message_pygit_bugs(
            self.project.NAME
        )

        return _union_commit_message_and_issue_event_pygit_bugs(
            issue_event_bugs, commit_msg_bugs
        )

    def find_all_raw_bugs(self) -> tp.FrozenSet[bug.RawBug]:
        """
        Creates a set for all bugs of the provider's project.

        Returns:
            A set of RawBugs.
        """
        if self.__github_project_name:
            issue_event_bugs = bug.find_all_issue_raw_bugs(self.project.NAME)
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_all_commit_message_raw_bugs(
            self.project.NAME
        )

        return _union_commit_message_and_issue_event_raw_bugs(
            issue_event_bugs, commit_msg_bugs
        )

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
            issue_event_bugs = bug.find_issue_pygit_bugs_by_fix(
                self.project.NAME, fixing_commit
            )
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_commit_message_pygit_bugs_by_fix(
            self.project.NAME, fixing_commit
        )

        return _union_commit_message_and_issue_event_pygit_bugs(
            issue_event_bugs, commit_msg_bugs
        )

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
            issue_event_bugs = bug.find_issue_raw_bugs_by_fix(
                self.project.NAME, fixing_commit
            )
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_commit_message_raw_bugs_by_fix(
            self.project.NAME, fixing_commit
        )

        return _union_commit_message_and_issue_event_raw_bugs(
            issue_event_bugs, commit_msg_bugs
        )

    def find_pygit_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.PygitBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain commit
        to the provider's project.

        Args:
            introducing_commit: commit hash of the introducing commit to look
                                for

        Returns:
            A set of PygitBugs introduced by introducing_commit
        """
        resulting_bugs: tp.Set[bug.PygitBug] = set()
        if self.__github_project_name:
            issue_event_bugs = bug.find_issue_pygit_bugs_by_introduction(
                self.project.NAME, introducing_commit
            )
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_commit_message_pygit_bugs_by_introduction(
            self.project.NAME, introducing_commit
        )

        return _union_commit_message_and_issue_event_pygit_bugs(
            issue_event_bugs, commit_msg_bugs
        )

    def find_raw_bug_by_introduction(
        self, introducing_commit: str
    ) -> tp.FrozenSet[bug.RawBug]:
        """
        Create a (potentially empty) list of bugs introduced by a certain
        commit.

        Args:
            introducing_commit: commit hash of the introducing commit to look
            for

        Returns:
            A set of RawBugs introduced by introducing_commit
        """
        if self.__github_project_name:
            issue_event_bugs = bug.find_issue_raw_bugs_by_introduction(
                self.project.NAME, introducing_commit
            )
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_commit_message_raw_bugs_by_introduction(
            self.project.NAME, introducing_commit
        )

        return _union_commit_message_and_issue_event_raw_bugs(
            issue_event_bugs, commit_msg_bugs
        )


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

"""Module for the :class:`BugProvider`."""
import logging
import typing as tp

from benchbuild.project import Project

from varats.project.project_util import (
    get_primary_project_source,
    is_git_source,
)
from varats.provider.bug import bug
from varats.provider.provider import Provider
from varats.utils.github_util import get_github_repo_name_for_project

LOG = logging.getLogger(__name__)


def _union_commit_message_and_issue_event_bugs(
    issue_event_bugs: tp.FrozenSet[bug.PygitBug],
    commit_message_bugs: tp.FrozenSet[bug.PygitBug]
) -> tp.FrozenSet[bug.PygitBug]:
    """
    Custom union of sets of commit message and issue event bugs.

    Commit message bugs only get added if there is no issue event bug with the
    same fixing commit.

    Args:
        issue_event_bugs: set of issue event bugs
        commit_message_bugs: set of commit message bugs

    Returns:
        union of the sets of bugs
    """
    union: tp.Set[bug.PygitBug] = set()
    union.update(issue_event_bugs)

    for commit_message_bug in commit_message_bugs:
        if commit_message_bug.fixing_commit not in {
            issue_event_bug.fixing_commit
            for issue_event_bug in issue_event_bugs
        }:
            union.add(commit_message_bug)

    return frozenset(union)


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

    def find_pygit_bugs(
        self,
        fixing_commit: tp.Optional[str] = None,
        introducing_commit: tp.Optional[str] = None
    ) -> tp.FrozenSet[bug.PygitBug]:
        """
        Find bugs in the provider's project.

        Args:
            fixing_commit: if given, only return bugs that are fixed by that
                           commit
            introducing_commit: if given, only return bugs that are (partially)
                                introduced by this commit

        Returns:
            a set of ``PygitBugs``
        """
        if self.__github_project_name:
            issue_event_bugs = bug.find_issue_bugs(
                self.project.NAME, fixing_commit, introducing_commit
            )
        else:
            issue_event_bugs = frozenset()

        commit_msg_bugs = bug.find_commit_message_bugs(
            self.project.NAME, fixing_commit, introducing_commit
        )

        return _union_commit_message_and_issue_event_bugs(
            issue_event_bugs, commit_msg_bugs
        )

    def find_raw_bugs(
        self,
        fixing_commit: tp.Optional[str] = None,
        introducing_commit: tp.Optional[str] = None
    ) -> tp.FrozenSet[bug.RawBug]:
        """
        Find bugs in the provider's project.

        Args:
            fixing_commit: if given, only return bugs that are fixed by that
                           commit
            introducing_commit: if given, only return bugs that are (partially)
                                introduced by this commit

        Returns:
            a set of ``RawBugs``
        """
        return frozenset([
            bug.as_raw_bug(pygit_bug) for pygit_bug in
            self.find_pygit_bugs(fixing_commit, introducing_commit)
        ])


class BugDefaultProvider(BugProvider):
    """Default implementation of the :class:`Bug provider` for projects that do
    not (yet) support bugs."""

    def __init__(self, project: tp.Type[Project]) -> None:
        # pylint: disable=E1003
        super(BugProvider, self).__init__(project)

    def find_pygit_bugs(
        self,
        fixing_commit: tp.Optional[str] = None,
        introducing_commit: tp.Optional[str] = None
    ) -> tp.FrozenSet[bug.PygitBug]:
        return frozenset()

    def find_raw_bugs(
        self,
        fixing_commit: tp.Optional[str] = None,
        introducing_commit: tp.Optional[str] = None
    ) -> tp.FrozenSet[bug.RawBug]:
        return frozenset()

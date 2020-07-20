"""Bug Classes used by bug_provider."""

import typing as tp

import pygit2
from github import Github
from github.IssueEvent import IssueEvent
from github.PaginatedList import PaginatedList
from github.Repository import Repository

from varats.utils.github_util import get_cached_github_object
from varats.utils.project_util import (
    get_local_project_git_path,
    get_local_project_git,
)


class PygitBug:
    """Bug representation using the ``pygit2.Commit`` class."""

    def __init__(
        self, fixing_commit: pygit2.Commit,
        introducing_commits: tp.List[pygit2.Commit], issue_id: int
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = introducing_commits
        self.__issue_id = issue_id

    @property
    def fixing_commit(self) -> pygit2.Commit:
        """Commit fixing the bug as pygit2 Commit."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.List[pygit2.Commit]:
        """Commits introducing the bug as List of pygit2 Commits."""
        return self.__introducing_commits

    @property
    def issue_id(self) -> int:
        """ID of the issue associated with the bug."""
        return self.__issue_id


class RawBug:
    """Bug representation using the Commit Hashes as Strings."""

    def __init__(
        self, fixing_commit: str, introducing_commits: tp.List[str],
        issue_id: int
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = introducing_commits
        self.__issue_id = issue_id

    @property
    def fixing_commit(self) -> str:
        """Hash of the commit fixing the bug as string."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.List[str]:
        """Hashes of the commits introducing the bug as List of strings."""
        return self.__introducing_commits

    @property
    def issue_id(self) -> int:
        """ID of the issue associated with the bug."""
        return self.__issue_id


def _get_all_issue_events(
    project_name: str
) -> tp.Optional[tp.List[IssueEvent]]:
    """
    Loads and returns all issue events from a given project.

    :param project_name:
        The name of the project to look in.
    :return: A list of IssueEvent objects or None.
    """

    def load_issue_events(github: Github) -> PaginatedList:
        repository: Repository = github.get_repo(project_name)
        return repository.get_issues_events()

    repo_path = get_local_project_git_path(project_name)
    cache_file_name = repo_path.name.replace("/", "_") + "_issues_events"

    return get_cached_github_object(cache_file_name, load_issue_events)


def _has_closed_a_bug(issue_event: IssueEvent) -> bool:
    """
    Decides for a given issue event whether it closes an issue representing a
    bug or not.

    :param issue_event:
        the issue event to be checked
    :return:
        true if the issue represents a bug and the issue event closed that issue,
        false ow.
    """
    if issue_event.event != "closed" or issue_event.commit_id is None:
        return False
    for label in issue_event.issue.labels:
        if label.name == "bug":
            return True
    return False


def find_all_pygit_bugs(project_name: str) -> tp.FrozenSet[PygitBug]:
    """
    Creates a set of all bugs.

    :param project_name:
        Name of the project in which to search for bugs
    :return:
        A set of PygitBug Objects.
    """
    pygit_bugs: tp.Set[PygitBug] = set()

    issue_events = _get_all_issue_events(project_name)
    if issue_events:
        for issue_event in issue_events:
            if _has_closed_a_bug(issue_event):
                # TODO extract pygit2 Commit Objects from IssueEvent
                pygit_repo = get_local_project_git(project_name)

                fixing_id: str = issue_event.commit_id
                fixing_commit: pygit2.Commit = pygit_repo.revparse_single(
                    fixing_id
                )

                introducing_commits: tp.List[pygit2.Commit] = []

                pygit_bugs.add(
                    PygitBug(
                        fixing_commit, introducing_commits,
                        issue_event.issue.number
                    )
                )

    return frozenset(pygit_bugs)


def find_all_raw_bugs(project_name: str) -> tp.FrozenSet[RawBug]:
    """
    Creates a set of all bugs.

    :param project_name:
        Name of the project in which to search for bugs
    :return:
        A set of RawBug Objects.
    """
    raw_bugs: tp.Set[RawBug] = set()

    issue_events = _get_all_issue_events(project_name)
    if issue_events:
        for issue_event in issue_events:
            if _has_closed_a_bug(issue_event):
                fixing_id: str = issue_event.commit_id
                introducing_ids: tp.List[str] = []

                # TODO find introducing commits
                raw_bugs.add(
                    RawBug(
                        fixing_id, introducing_ids, issue_event.issue.number
                    )
                )
    return frozenset(raw_bugs)


def find_pygit_bug_by_fix(project_name: str,
                          fixing_commit: str) -> tp.Optional[PygitBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    :param project_name:
        Name of the project in which to search for bugs
    :param fixing_commit:
        Commit Hash of the potentially fixing commit
    :return:
        A PygitBug Object, if there is such a bug
        None, if there is no such bug
    """
    # TODO implement

    return None


def find_raw_bug_by_fix(project_name: str,
                        fixing_commit: str) -> tp.Optional[RawBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    :param project_name:
        Name of the project in which to search for bugs
    :param fixing_commit:
        Commit Hash of the potentially fixing commit
    :return:
        A RawBug Object, if there is such a bug
        None, if there is no such bug
    """
    # TODO implement

    return None


def find_pygit_bug_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.List[PygitBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    :param project_name:
        Name of the project in which to search for bugs
    :param introducing_commit:
        Commit Hash of the introducing commit to look for
    :return:
        A list of PygitBug Objects
    """
    # TODO implement

    return []


def find_raw_bug_by_introduction(project_name: str,
                                 introducing_commit: str) -> tp.List[RawBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    :param project_name:
        Name of the project in which to search for bugs
    :param introducing_commit:
        Commit Hash of the introducing commit to look for
    :return:
        A list of RawBug Objects
    """
    # TODO implement

    return []

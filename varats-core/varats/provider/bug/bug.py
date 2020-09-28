"""Bug Classes used by bug_provider."""

import typing as tp

import pygit2
from github import Github
from github.IssueEvent import IssueEvent
from github.PaginatedList import PaginatedList
from github.Repository import Repository

from varats.project.project_util import (
    get_local_project_git_path,
    get_local_project_git,
)
from varats.utils.github_util import get_cached_github_object_list


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


def _has_closed_a_bug(issue_event: IssueEvent) -> bool:
    """
    Determines for a given issue event whether it closes an issue representing a
    bug or not.

    Args:
        issue_event: the issue event to be checked

    Returns:
        true if the issue represents a bug and the issue event closed that issue
        false ow.
    """
    if issue_event.event != "closed" or issue_event.commit_id is None:
        return False
    for label in issue_event.issue.labels:
        if label.name == "bug":
            return True
    return False


def _get_all_issue_events(project_name: str) -> tp.List[IssueEvent]:
    """
    Loads and returns all issue events for a given project.

    Args:
        project_name: The name of the project to look in.

    Returns:
        A list of IssueEvent objects or None.
    """

    def load_issue_events(github: Github) -> PaginatedList[IssueEvent]:
        repository: Repository = github.get_repo(project_name)
        return repository.get_issues_events()

    repo_path = get_local_project_git_path(project_name)
    cache_file_name = repo_path.name.replace("/", "_") + "_issues_events"

    issue_events = get_cached_github_object_list(
        cache_file_name, load_issue_events
    )

    if issue_events:
        return issue_events
    return []


def _search_corresponding_pygit_bug(
    issue_event: IssueEvent, project_repo: pygit2.Repository
) -> tp.Optional[PygitBug]:
    """
    Returns the PygitBug corresponding to a given IssueEvent, if there is one.

    Args:
        issue_event: The Github IssueEvent potentially related to a bug
        project_repo: The related pygit2 project Repository

    Returns:
        A PygitBug Object or None.
    """
    if _has_closed_a_bug(issue_event):
        fixing_id = issue_event.commit_id

        if fixing_id is None:
            return None
        # unwrap option type
        fixing_id_string: str = fixing_id
        fixing_pycommit: pygit2.Commit = project_repo.revparse_single(
            fixing_id_string
        )

        introducing_pycommits: tp.List[pygit2.Commit] = []
        # TODO find introducing commits

        return PygitBug(
            fixing_pycommit, introducing_pycommits, issue_event.issue.number
        )
    return None


def _search_corresponding_raw_bug(
    issue_event: IssueEvent, project_repo: pygit2.Repository
) -> tp.Optional[RawBug]:
    """
    Returns the RawBug corresponding to a given IssueEvent, if there is one.

    Args:
        issue_event: The Github IssueEvent potentially related to a bug
        project_repo: The related pygit2 project Repository

    Returns:
        A RawBug Object or None.
    """
    if _has_closed_a_bug(issue_event):
        fixing_id = issue_event.commit_id

        if fixing_id is None:
            return None
        # unwrap option type
        fixing_id_string: str = fixing_id

        introducing_ids: tp.List[str] = []

        # TODO find introducing commits

        return RawBug(
            fixing_id_string, introducing_ids, issue_event.issue.number
        )
    return None


def _filter_pygit_bugs_for_all_issue_events(
    project_name: str, issue_filter_function: tp.Callable[[IssueEvent],
                                                          tp.Optional[PygitBug]]
) -> tp.FrozenSet[PygitBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    PygitBugs.

    Args:
        project_name: Name of the project to draw the issue events out of.
        issue_filter_function: Function that determines for an issue event
            whether it produces an acceptable PygitBug or not.

    Returns:
        The set of PygitBugs accepted by the filtering method.
    """
    resulting_pygit_bugs = set()

    issue_events = _get_all_issue_events(project_name)
    for issue_event in issue_events:
        pybug = issue_filter_function(issue_event)
        if pybug:
            resulting_pygit_bugs.add(pybug)
    return frozenset(resulting_pygit_bugs)


def _filter_raw_bugs_for_all_issue_events(
    project_name: str, issue_filter_function: tp.Callable[[IssueEvent],
                                                          tp.Optional[RawBug]]
) -> tp.FrozenSet[RawBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    RawBugs.

    Args:
        project_name: Name of the project to draw the issue events out of.
        issue_filter_function: Function that determines for an issue event
            whether it produces an acceptable RawBug or not.

    Returns:
        The set of RawBugs accepted by the filtering method.
    """
    resulting_raw_bugs = set()

    issue_events = _get_all_issue_events(project_name)
    for issue_event in issue_events:
        rawbug = issue_filter_function(issue_event)
        if rawbug:
            resulting_raw_bugs.add(rawbug)
    return frozenset(resulting_raw_bugs)


def find_all_pygit_bugs(project_name: str) -> tp.FrozenSet[PygitBug]:
    """
    Creates a set of all bugs.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of PygitBugs.
    """

    def accept_all_pybugs(issue_event: IssueEvent) -> tp.Optional[PygitBug]:
        pygit_repo: pygit2.Repository = get_local_project_git(project_name)
        return _search_corresponding_pygit_bug(issue_event, pygit_repo)

    return _filter_pygit_bugs_for_all_issue_events(
        project_name, accept_all_pybugs
    )


def find_all_raw_bugs(project_name: str) -> tp.FrozenSet[RawBug]:
    """
    Creates a set of all bugs.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of RawBugs.
    """

    def accept_all_rawbugs(issue_event: IssueEvent) -> tp.Optional[RawBug]:
        pygit_repo: pygit2.Repository = get_local_project_git(project_name)
        return _search_corresponding_raw_bug(issue_event, pygit_repo)

    return _filter_raw_bugs_for_all_issue_events(
        project_name, accept_all_rawbugs
    )


def find_pygit_bug_by_fix(project_name: str,
                          fixing_commit: str) -> tp.FrozenSet[PygitBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of PygitBugs fixed by fixing_commit
    """

    def accept_pybug_with_certain_fix(
        issue_event: IssueEvent
    ) -> tp.Optional[PygitBug]:
        pygit_repo: pygit2.Repository = get_local_project_git(project_name)
        pybug: tp.Optional[PygitBug] = _search_corresponding_pygit_bug(
            issue_event, pygit_repo
        )

        if pybug:
            if pybug.fixing_commit.hex is fixing_commit:
                return pybug
        return None

    return _filter_pygit_bugs_for_all_issue_events(
        project_name, accept_pybug_with_certain_fix
    )


def find_raw_bug_by_fix(project_name: str,
                        fixing_commit: str) -> tp.FrozenSet[RawBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of RawBugs fixed by fixing_commit
    """

    def accept_rawbug_with_certain_fix(
        issue_event: IssueEvent
    ) -> tp.Optional[RawBug]:
        pygit_repo: pygit2.Repository = get_local_project_git(project_name)
        rawbug: tp.Optional[RawBug] = _search_corresponding_raw_bug(
            issue_event, pygit_repo
        )

        if rawbug:
            if rawbug.fixing_commit is fixing_commit:
                return rawbug
        return None

    return _filter_raw_bugs_for_all_issue_events(
        project_name, accept_rawbug_with_certain_fix
    )


def find_pygit_bug_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[PygitBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of PygitBugs introduced by introducing_commit
    """

    def accept_pybug_with_certain_introduction(
        issue_event: IssueEvent
    ) -> tp.Optional[PygitBug]:
        pygit_repo = get_local_project_git(project_name)
        pybug: tp.Optional[PygitBug] = _search_corresponding_pygit_bug(
            issue_event, pygit_repo
        )

        if pybug:
            for introducing_pycommit in pybug.introducing_commits:
                if introducing_pycommit.hex is introducing_commit:
                    return pybug
                    # found wanted ID
        return None

    return _filter_pygit_bugs_for_all_issue_events(
        project_name, accept_pybug_with_certain_introduction
    )


def find_raw_bug_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[RawBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of RawBugs introduced by introducing_commit
    """

    def accept_rawbug_with_certain_introduction(
        issue_event: IssueEvent
    ) -> tp.Optional[RawBug]:
        pygit_repo: pygit2.Repository = get_local_project_git(project_name)
        rawbug: tp.Optional[RawBug] = _search_corresponding_raw_bug(
            issue_event, pygit_repo
        )

        if rawbug:
            for introducing_id in rawbug.introducing_commits:
                if introducing_id is introducing_commit:
                    return rawbug
                    # found wanted ID
        return None

    return _filter_raw_bugs_for_all_issue_events(
        project_name, accept_rawbug_with_certain_introduction
    )

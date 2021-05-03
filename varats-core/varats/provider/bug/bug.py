"""Bug Classes used by bug_provider."""

import typing as tp
from datetime import datetime

import pydriller
import pygit2
from github import Github
from github.IssueEvent import IssueEvent
from github.Repository import Repository

from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.utils.github_util import (
    get_cached_github_object_list,
    get_github_repo_name_for_project,
)

if tp.TYPE_CHECKING:
    # pylint: disable=ungrouped-imports,unused-import
    from github.PaginatedList import PaginatedList


class PygitBug:
    """Bug representation using the ``pygit2.Commit`` class."""

    def __init__(
        self,
        fixing_commit: pygit2.Commit,
        introducing_commits: tp.Set[pygit2.Commit],
        issue_id: tp.Optional[int],
        creationdate: tp.Optional[datetime] = None,
        resolutiondate: tp.Optional[datetime] = None
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = frozenset(introducing_commits)
        self.__issue_id = issue_id
        self.__creationdate = creationdate
        self.__resolutiondate = resolutiondate

    @property
    def fixing_commit(self) -> pygit2.Commit:
        """Commit fixing the bug as pygit2 Commit."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.FrozenSet[pygit2.Commit]:
        """Commits introducing the bug as List of pygit2 Commits."""
        return self.__introducing_commits

    @property
    def issue_id(self) -> tp.Optional[int]:
        """ID of the issue associated with the bug, if there is one."""
        return self.__issue_id

    @property
    def creationdate(self) -> tp.Optional[datetime]:
        """Creation date of the associated issue, if there is one."""
        return self.__creationdate

    @property
    def resolutiondate(self) -> tp.Optional[datetime]:
        """Resolution date of the associated issue, if there is one."""
        return self.__resolutiondate

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PygitBug):
            return (
                self.fixing_commit == other.fixing_commit and
                self.introducing_commits == other.introducing_commits and
                self.issue_id == other.issue_id
            )
        return False

    def __hash__(self) -> int:
        return hash(
            (self.fixing_commit, self.introducing_commits, self.issue_id)
        )


class RawBug:
    """Bug representation using the Commit Hashes as Strings."""

    def __init__(
        self,
        fixing_commit: str,
        introducing_commits: tp.Set[str],
        issue_id: tp.Optional[int],
        creationdate: tp.Optional[datetime] = None,
        resolutiondate: tp.Optional[datetime] = None
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = frozenset(introducing_commits)
        self.__issue_id = issue_id
        self.__creationdate = creationdate
        self.__resolutiondate = resolutiondate

    @property
    def fixing_commit(self) -> str:
        """Hash of the commit fixing the bug as string."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.FrozenSet[str]:
        """Hashes of the commits introducing the bug as List of strings."""
        return self.__introducing_commits

    @property
    def issue_id(self) -> tp.Optional[int]:
        """ID of the issue associated with the bug, if there is one."""
        return self.__issue_id

    @property
    def creationdate(self) -> tp.Optional[datetime]:
        """Creation date of the associated issue, if there is one."""
        return self.__creationdate

    @property
    def resolutiondate(self) -> tp.Optional[datetime]:
        """Resolution date of the associated issue, if there is one."""
        return self.__resolutiondate

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RawBug):
            return (
                self.fixing_commit == other.fixing_commit and
                self.introducing_commits == other.introducing_commits and
                self.issue_id == other.issue_id
            )
        return False

    def __hash__(self) -> int:
        return hash(
            (self.fixing_commit, self.introducing_commits, self.issue_id)
        )


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


def _is_closing_message(commit_message: str) -> bool:
    """
    Determines for a given commit message whether it indicates that a bug has
    been closed by the corresponding commit.

    Args:
        commit_message: the commit message to be checked

    Returns:
        true if the commit message contains key words that indicate the
        closing of a bug, false ow.
    """
    # only look for keyword in first line of commit message
    first_line = commit_message.partition('\n')[0]

    return any([
        keyword in first_line.split()
        for keyword in ['fix', 'Fix', 'fixed', 'Fixed', 'fixes', 'Fixes']
    ])


def _get_all_issue_events(project_name: str) -> tp.List[IssueEvent]:
    """
    Loads and returns all issue events for a given project.

    Args:
        project_name: The name of the project to look in.

    Returns:
        A list of IssueEvent objects or None.
    """

    github_repo_name = get_github_repo_name_for_project(
        get_project_cls_by_name(project_name)
    )

    if github_repo_name:

        def load_issue_events(github: Github) -> 'PaginatedList[IssueEvent]':
            if github_repo_name:
                repository: Repository = github.get_repo(github_repo_name)
                return repository.get_issues_events()
            # Method should only be called when loading issue
            # events for a github repo
            raise AssertionError(
                f"No github repo found for project {project_name}"
            )

        cache_file_name = github_repo_name.replace("/", "_") + "_issues_events"

        issue_events = get_cached_github_object_list(
            cache_file_name, load_issue_events
        )

        if issue_events:
            return issue_events
        return []
    # No github repo; Should not occur at this point
    raise AssertionError(f"No github repo found for project {project_name}")


def _create_corresponding_pygit_bug(
    closing_commit: str,
    project_repo: pygit2.Repository,
    issue_number: tp.Optional[int] = None,
    creationdate: tp.Optional[datetime] = None,
    resolutiondate: tp.Optional[datetime] = None
) -> PygitBug:
    """
    Returns the PygitBug corresponding to a given closing commit. Applies simple
    SZZ algorithm to find introducing commits.

    Args:
        closing_commit: ID of the commit closing the bug.
        project_repo: The related pygit2 project Repository
        issue_number: The bug's issue number if there is an issue
            related to the bug.

    Returns:
        A PygitBug Object or None.
    """

    pydrill_repo = pydriller.GitRepository(project_repo.path)

    closing_pycommit: pygit2.Commit = project_repo.revparse_single(
        closing_commit
    )
    introducing_pycommits: tp.Set[pygit2.Commit] = set()

    blame_dict = pydrill_repo.get_commits_last_modified_lines(
        pydrill_repo.get_commit(closing_commit)
    )

    for _, introducing_set in blame_dict.items():
        for introducing_id in introducing_set:
            introducing_pycommits.add(
                project_repo.revparse_single(introducing_id)
            )

    return PygitBug(
        closing_pycommit, introducing_pycommits, issue_number, creationdate,
        resolutiondate
    )


def _create_corresponding_raw_bug(
    closing_commit: str,
    project_repo: pygit2.Repository,
    issue_number: tp.Optional[int] = None,
    creationdate: tp.Optional[datetime] = None,
    resolutiondate: tp.Optional[datetime] = None
) -> RawBug:
    """
    Returns the RawBug corresponding to a given closing commit. Applies simple
    SZZ algorithm to find introducing commits.

    Args:
        closing_commit: ID of the commit closing the bug.
        project_repo: The related pygit2 project Repository
        issue_number: The bug's issue number if there is an issue
            related to the bug.

    Returns:
        A RawBug Object or None.
    """
    pydrill_repo = pydriller.GitRepository(project_repo.path)

    introducing_ids: tp.Set[str] = set()

    blame_dict = pydrill_repo.get_commits_last_modified_lines(
        pydrill_repo.get_commit(closing_commit)
    )

    for _, introducing_set in blame_dict.items():
        introducing_ids.update(introducing_set)

    return RawBug(
        closing_commit, introducing_ids, issue_number, creationdate,
        resolutiondate
    )


def _filter_all_issue_pygit_bugs(
    project_name: str, issue_filter_function: tp.Callable[[IssueEvent],
                                                          tp.Optional[PygitBug]]
) -> tp.FrozenSet[PygitBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    PygitBugs using issue events.

    Args:
        project_name: Name of the project to draw the issue events and
            commit history out of.
        issue_filter_function: Function that determines for an issue event
            whether it produces an acceptable PygitBug or not.

    Returns:
        The set of PygitBugs considered acceptable by the filtering method.
    """
    resulting_pygit_bugs = set()

    # iterate over all issue events
    issue_events = _get_all_issue_events(project_name)
    for issue_event in issue_events:
        pybug = issue_filter_function(issue_event)
        if pybug:
            resulting_pygit_bugs.add(pybug)

    return frozenset(resulting_pygit_bugs)


def _filter_all_issue_raw_bugs(
    project_name: str, issue_filter_function: tp.Callable[[IssueEvent],
                                                          tp.Optional[RawBug]]
) -> tp.FrozenSet[RawBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    RawBugs using issue events.

    Args:
        project_name: Name of the project to draw the issue events and
            commit history out of.
        issue_filter_function: Function that determines for an issue event
            whether it produces an acceptable RawBug or not.

    Returns:
        The set of RawBugs considered acceptable by the filtering method.
    """
    resulting_raw_bugs = set()

    # iterate over all issue events
    issue_events = _get_all_issue_events(project_name)
    for issue_event in issue_events:
        rawbug = issue_filter_function(issue_event)
        if rawbug:
            resulting_raw_bugs.add(rawbug)

    return frozenset(resulting_raw_bugs)


def _filter_all_commit_message_pygit_bugs(
    project_name: str,
    commit_filter_function: tp.Callable[[pygit2.Commit], tp.Optional[PygitBug]]
) -> tp.FrozenSet[PygitBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    PygitBugs using the commit history.

    Args:
        project_name: Name of the project to draw the commit history from.
        commit_filter_function: Function that determines for a commit
            whether it produces an acceptable PygitBug or not.

    Returns:
        The set of PygitBugs considered acceptable by the filtering method.
    """
    resulting_pygit_bugs = set()
    project_repo = get_local_project_git(project_name)

    # traverse commit history
    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        pybug = commit_filter_function(commit)
        if pybug:
            resulting_pygit_bugs.add(pybug)

    return frozenset(resulting_pygit_bugs)


def _filter_all_commit_message_raw_bugs(
    project_name: str, commit_filter_function: tp.Callable[[pygit2.Commit],
                                                           tp.Optional[RawBug]]
) -> tp.FrozenSet[RawBug]:
    """
    Wrapper function that uses given function to filter out a certain type of
    RawBugs using the commit history.

    Args:
        project_name: Name of the project to draw the commit history from.
        commit_filter_function: Function that determines for a commit
            whether it produces an acceptable RawBug or not.

    Returns:
        The set of RawBugs considered acceptable by the filtering method.
    """
    resulting_raw_bugs = set()
    project_repo = get_local_project_git(project_name)

    # traverse commit history
    most_recent_commit = project_repo[project_repo.head.target]
    for commit in project_repo.walk(
        most_recent_commit.id, pygit2.GIT_SORT_TIME
    ):
        rawbug = commit_filter_function(commit)
        if rawbug:
            resulting_raw_bugs.add(rawbug)

    return frozenset(resulting_raw_bugs)


def find_all_issue_pygit_bugs(project_name: str) -> tp.FrozenSet[PygitBug]:
    """
    Creates a set of all bugs related to issue events.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of PygitBugs.
    """

    def accept_all_issue_pybugs(
        issue_event: IssueEvent
    ) -> tp.Optional[PygitBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            return _create_corresponding_pygit_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )
        return None

    return _filter_all_issue_pygit_bugs(project_name, accept_all_issue_pybugs)


def find_all_issue_raw_bugs(project_name: str) -> tp.FrozenSet[RawBug]:
    """
    Creates a set of all bugs related to issue events.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of RawBugs.
    """

    def accept_all_issue_rawbugs(
        issue_event: IssueEvent
    ) -> tp.Optional[RawBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            return _create_corresponding_raw_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )
        return None

    return _filter_all_issue_raw_bugs(project_name, accept_all_issue_rawbugs)


def find_issue_pygit_bugs_by_fix(project_name: str,
                                 fixing_commit: str) -> tp.FrozenSet[PygitBug]:
    """
    Find the bug associated to some fixing commit, if there is any, using issue
    events.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of PygitBugs fixed by fixing_commit
    """

    def accept_issue_pybug_with_certain_fix(
        issue_event: IssueEvent
    ) -> tp.Optional[PygitBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            pybug = _create_corresponding_pygit_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )
            if pybug.fixing_commit.hex == fixing_commit:
                return pybug
        return None

    return _filter_all_issue_pygit_bugs(
        project_name, accept_issue_pybug_with_certain_fix
    )


def find_issue_raw_bugs_by_fix(project_name: str,
                               fixing_commit: str) -> tp.FrozenSet[RawBug]:
    """
    Find the bug associated to some fixing commit, if there is any, using issue
    events.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of RawBugs fixed by fixing_commit
    """

    def accept_issue_rawbug_with_certain_fix(
        issue_event: IssueEvent
    ) -> tp.Optional[RawBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            rawbug = _create_corresponding_raw_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )
            if rawbug.fixing_commit == fixing_commit:
                return rawbug
        return None

    return _filter_all_issue_raw_bugs(
        project_name, accept_issue_rawbug_with_certain_fix
    )


def find_issue_pygit_bugs_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[PygitBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit
    using issue events.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of PygitBugs introduced by introducing_commit
    """

    def accept_issue_pybug_with_certain_introduction(
        issue_event: IssueEvent
    ) -> tp.Optional[PygitBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo = get_local_project_git(project_name)
            pybug = _create_corresponding_pygit_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )

            for introducing_pycommit in pybug.introducing_commits:
                if introducing_pycommit.hex == introducing_commit:
                    return pybug
                    # found wanted ID
        return None

    return _filter_all_issue_pygit_bugs(
        project_name, accept_issue_pybug_with_certain_introduction
    )


def find_issue_raw_bugs_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[RawBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit
    using issue events.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of RawBugs introduced by introducing_commit
    """

    def accept_issue_rawbug_with_certain_introduction(
        issue_event: IssueEvent
    ) -> tp.Optional[RawBug]:
        if _has_closed_a_bug(issue_event) and issue_event.commit_id:
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            rawbug = _create_corresponding_raw_bug(
                issue_event.commit_id, pygit_repo, issue_event.issue.number,
                issue_event.issue.created_at, issue_event.issue.closed_at
            )

            for introducing_id in rawbug.introducing_commits:
                if introducing_id == introducing_commit:
                    return rawbug
                    # found wanted ID
        return None

    return _filter_all_issue_raw_bugs(
        project_name, accept_issue_rawbug_with_certain_introduction
    )


def find_all_commit_message_pygit_bugs(
    project_name: str
) -> tp.FrozenSet[PygitBug]:
    """
    Creates a set of all bugs found in the commit history of a project.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of PygitBugs
    """

    def accept_all_commit_message_pybugs(
        commit: pygit2.Commit
    ) -> tp.Optional[PygitBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            return _create_corresponding_pygit_bug(commit.hex, pygit_repo)
        return None

    return _filter_all_commit_message_pygit_bugs(
        project_name, accept_all_commit_message_pybugs
    )


def find_all_commit_message_raw_bugs(project_name: str) -> tp.FrozenSet[RawBug]:
    """
    Creates a set of all bugs found in the commit history of a project.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of PygitBugs
    """

    def accept_all_commit_message_rawbugs(
        commit: pygit2.Commit
    ) -> tp.Optional[RawBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            return _create_corresponding_raw_bug(commit.hex, pygit_repo)
        return None

    return _filter_all_commit_message_raw_bugs(
        project_name, accept_all_commit_message_rawbugs
    )


def find_commit_message_pygit_bugs_by_fix(
    project_name: str, fixing_commit: str
) -> tp.FrozenSet[PygitBug]:
    """
    Traverses the commit history of given project to find the bug associated to
    some fixing commit, if there is any.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of PygitBugs fixed by fixing_commit
    """

    def accept_commit_message_pybug_with_certain_fix(
        commit: pygit2.Commit
    ) -> tp.Optional[PygitBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            pybug = _create_corresponding_pygit_bug(commit.hex, pygit_repo)
            if pybug.fixing_commit.hex == fixing_commit:
                return pybug
        return None

    return _filter_all_commit_message_pygit_bugs(
        project_name, accept_commit_message_pybug_with_certain_fix
    )


def find_commit_message_raw_bugs_by_fix(
    project_name: str, fixing_commit: str
) -> tp.FrozenSet[RawBug]:
    """
    Traverses the commit history of given project to find the bug associated to
    some fixing commit, if there is any.

    Args:
        project_name: Name of the project in which to search for bugs
        fixing_commit: Commit Hash of the potentially fixing commit

    Returns:
        A set of RawBugs fixed by fixing_commit
    """

    def accept_commit_message_rawbug_with_certain_fix(
        commit: pygit2.Commit
    ) -> tp.Optional[RawBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            rawbug = _create_corresponding_raw_bug(commit.hex, pygit_repo)
            if rawbug.fixing_commit == fixing_commit:
                return rawbug
        return None

    return _filter_all_commit_message_raw_bugs(
        project_name, accept_commit_message_rawbug_with_certain_fix
    )


def find_commit_message_pygit_bugs_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[PygitBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit by
    traversing the commit history of given project.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of PygitBugs introduced by introducing_commit
    """

    def accept_commit_message_pybug_with_certain_introduction(
        commit: pygit2.Commit
    ) -> tp.Optional[PygitBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            pybug = _create_corresponding_pygit_bug(commit.hex, pygit_repo)

            for introducing_pycommit in pybug.introducing_commits:
                if introducing_pycommit.hex == introducing_commit:
                    return pybug
        return None

    return _filter_all_commit_message_pygit_bugs(
        project_name, accept_commit_message_pybug_with_certain_introduction
    )


def find_commit_message_raw_bugs_by_introduction(
    project_name: str, introducing_commit: str
) -> tp.FrozenSet[RawBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit by
    traversing the commit history of given project.

    Args:
        project_name: Name of the project in which to search for bugs
        introducing_commit: Commit Hash of the introducing commit to look for

    Returns:
        A set of PygitBugs introduced by introducing_commit
    """

    def accept_commit_message_rawbug_with_certain_introduction(
        commit: pygit2.Commit
    ) -> tp.Optional[RawBug]:
        if _is_closing_message(commit.message):
            pygit_repo: pygit2.Repository = get_local_project_git(project_name)
            rawbug = _create_corresponding_raw_bug(commit.hex, pygit_repo)

            for introducing_id in rawbug.introducing_commits:
                if introducing_id == introducing_commit:
                    return rawbug
        return None

    return _filter_all_commit_message_raw_bugs(
        project_name, accept_commit_message_rawbug_with_certain_introduction
    )

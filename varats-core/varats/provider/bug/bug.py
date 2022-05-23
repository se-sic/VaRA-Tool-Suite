"""Bug Classes used by bug_provider."""

import typing as tp
from datetime import datetime, timezone

import pydriller
import pygit2
from github import Github
from github.IssueEvent import IssueEvent

from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.utils.git_util import FullCommitHash
from varats.utils.github_util import (
    get_cached_github_object_list,
    get_github_repo_name_for_project,
)

if tp.TYPE_CHECKING:
    # pylint: disable=ungrouped-imports,unused-import
    from github.PaginatedList import PaginatedList

CommitTy = tp.TypeVar("CommitTy")


class Bug(tp.Generic[CommitTy]):
    """Generic class for representing bugs along with its introducing and fixing
    commits."""

    def __init__(
        self,
        fixing_commit: CommitTy,
        introducing_commits: tp.Set[CommitTy],
        issue_id: tp.Optional[int] = None,
        creationdate: tp.Optional[datetime] = None,
        resolutiondate: tp.Optional[datetime] = None
    ) -> None:
        self.__fixing_commit: CommitTy = fixing_commit
        self.__introducing_commits: tp.FrozenSet[CommitTy] = frozenset(
            introducing_commits
        )
        self.__issue_id = issue_id
        self.__creationdate = creationdate
        self.__resolutiondate = resolutiondate

    @property
    def fixing_commit(self) -> CommitTy:
        """Commit fixing the bug."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.FrozenSet[CommitTy]:
        """List of commits introducing the bug."""
        return self.__introducing_commits

    @property
    def issue_id(self) -> tp.Optional[int]:
        """ID of the issue associated with the bug, if there is one."""
        return self.__issue_id

    @property
    def creation_date(self) -> tp.Optional[datetime]:
        """Creation date of the associated issue, if there is one."""
        return self.__creationdate

    @property
    def resolution_date(self) -> tp.Optional[datetime]:
        """Resolution date of the associated issue, if there is one."""
        return self.__resolutiondate

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Bug):
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


RawBug = Bug[FullCommitHash]
PygitBug = Bug[pygit2.Commit]


def as_raw_bug(pygit_bug: PygitBug) -> RawBug:
    """Converts a ``PygitBug`` to a ``RawBug``."""
    introducing_commits: tp.Set[FullCommitHash] = set()
    for intro_commit in pygit_bug.introducing_commits:
        introducing_commits.add(FullCommitHash.from_pygit_commit(intro_commit))
    return RawBug(
        FullCommitHash.from_pygit_commit(pygit_bug.fixing_commit),
        introducing_commits, pygit_bug.issue_id, pygit_bug.creation_date,
        pygit_bug.resolution_date
    )


def as_pygit_bug(raw_bug: RawBug, repo: pygit2.Repository) -> PygitBug:
    """Converts a ``RawBug`` to a ``PygitBug``."""
    introducing_commits: tp.Set[pygit2.Commit] = set()
    for intro_commit in raw_bug.introducing_commits:
        introducing_commits.add(repo.get(intro_commit))
    return PygitBug(
        repo.get(raw_bug.fixing_commit.hash), introducing_commits,
        raw_bug.issue_id, raw_bug.creation_date, raw_bug.resolution_date
    )


class PygitSuspectTuple:
    """Helper class to classify bug suspects."""

    def __init__(
        self, fixing_commit: pygit2.Commit, non_suspects: tp.Set[pygit2.Commit],
        uncleared_suspects: tp.Set[pygit2.Commit], issue_id: int,
        creation_date: datetime, resolution_date: datetime
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__non_suspects = non_suspects
        self.__cleared_suspects: tp.Set[pygit2.Commit] = set()
        self.__uncleared_suspects = uncleared_suspects
        self.__issue_id = issue_id
        self.__creationdate = creation_date
        self.__resolutiondate = resolution_date

    @property
    def fixing_commit(self) -> pygit2.Commit:
        """Hash of the commit fixing the bug as pygit2 Commit."""
        return self.__fixing_commit

    @property
    def non_suspects(self) -> tp.FrozenSet[pygit2.Commit]:
        """Introducing Commits that were authored before the bug report."""
        return frozenset(self.__non_suspects)

    def is_cleared(self) -> bool:
        """Returns whether all suspects inside this tuple have been cleared."""
        return len(self.__uncleared_suspects) == 0

    def consume_uncleared_suspects(
        self
    ) -> tp.Generator[pygit2.Commit, None, None]:
        """Iterate over and comsume uncleared suspects."""
        while not self.is_cleared():
            yield self.__uncleared_suspects.pop()

    def clear_suspect(self, cleared_suspect: pygit2.Commit) -> None:
        """Adds parameter cleared_suspect to cleared suspects."""
        self.__cleared_suspects.add(cleared_suspect)

    def create_corresponding_bug(self) -> PygitBug:
        """Uses cleared suspects and non-suspects to create a PygitBug."""
        if not self.is_cleared():
            raise AssertionError
        introducing_commits = self.__non_suspects.union(self.__cleared_suspects)
        return PygitBug(
            self.__fixing_commit, introducing_commits, self.__issue_id,
            self.__creationdate, self.__resolutiondate
        )


def _has_closed_a_bug(issue_event: IssueEvent) -> bool:
    """
    Determines for a given issue event whether it closes a bug or not.

    Args:
        issue_event: the issue event to be checked

    Returns:
        whether the issue event closed a bug or not
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
        whether the commit message closes a bug or not
    """
    # only look for keyword in first line of commit message
    first_line = commit_message.partition('\n')[0]

    return any(
        keyword in first_line.split()
        for keyword in ['fix', 'Fix', 'fixed', 'Fixed', 'fixes', 'Fixes']
    )


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
                return github.get_repo(github_repo_name).get_issues_events()

            raise AssertionError(f"{project_name} is not a github project")

        cache_file_name = github_repo_name.replace("/", "_") + "_issues_events"
        issue_events = get_cached_github_object_list(
            cache_file_name, load_issue_events
        )

        if issue_events:
            return issue_events
        return []

    raise AssertionError(f"{project_name} is not a github project")


def _create_corresponding_bug(
    closing_commit: pygit2.Commit,
    project_repo: pygit2.Repository,
    issue_id: tp.Optional[int] = None,
    creation_date: tp.Optional[datetime] = None,
    resolution_date: tp.Optional[datetime] = None
) -> PygitBug:
    """
    Create the bug corresponding to a given closing commit.

    Applies simple SZZ algorithm as implemented in pydriller to find introducing
    commits.

    Args:
        closing_commit: commit closing the bug.
        project_repo: pygit2 repository of the project
        issue_id: optional issue number related to the bug

    Returns:
        the specified bug
    """
    pydrill_repo = pydriller.Git(project_repo.path)

    introducing_commits: tp.Set[pygit2.Commit] = set()
    blame_dict = pydrill_repo.get_commits_last_modified_lines(
        pydrill_repo.get_commit(str(closing_commit.id))
    )

    for _, introducing_set in blame_dict.items():
        for introducing_id in introducing_set:
            introducing_commits.add(project_repo.get(introducing_id))

    return PygitBug(
        closing_commit, introducing_commits, issue_id, creation_date,
        resolution_date
    )


def _find_corresponding_pygit_suspect_tuple(
    project_name: str, issue_event: IssueEvent
) -> tp.Optional[PygitSuspectTuple]:
    """
    Creates a suspect tuple given an issue event.

    Partitions the commits found via git blame on the fixing commit into
    suspects (commits after bug report) and non-suspects (commits before bug
    report).

    Args:
        project_name: Name of the project to draw the fixing and introducing
            commits from.
        issue_event: The IssueEvent potentially associated with a bug.

    Returns:
        A PygitSuspectTuple if the issue event represents the closing of a bug,
        None otherwise
    """
    pygit_repo: pygit2.Repository = get_local_project_git(project_name)
    pydrill_repo = pydriller.Git(pygit_repo.path)

    if _has_closed_a_bug(issue_event) and issue_event.commit_id:
        issue_date = issue_event.issue.created_at
        fixing_commit = pygit_repo.get(issue_event.commit_id)
        pydrill_fixing_commit = pydrill_repo.get_commit(issue_event.commit_id)
        blame_dict = pydrill_repo.get_commits_last_modified_lines(
            pydrill_fixing_commit
        )

        non_suspect_commits = set()
        suspect_commits = set()
        for introducing_set in blame_dict.values():
            for introducing_id in introducing_set:
                issue_date = issue_event.issue.created_at.astimezone(
                    timezone.utc
                )
                introduction_date = pydrill_repo.get_commit(
                    introducing_id
                ).committer_date.astimezone(timezone.utc)

                if introduction_date > issue_date:  # commit is a suspect
                    suspect_commits.add(pygit_repo.get(introducing_id))
                else:
                    non_suspect_commits.add(pygit_repo.get(introducing_id))

        return PygitSuspectTuple(
            fixing_commit, non_suspect_commits, suspect_commits,
            issue_event.issue.number, issue_event.issue.created_at,
            pydrill_fixing_commit.committer_date
        )
    return None


def _filter_issue_bugs(
    project_name: str, issue_events: tp.List[IssueEvent],
    suspect_filter_function: tp.Callable[[PygitSuspectTuple],
                                         tp.Optional[PygitBug]]
) -> tp.FrozenSet[PygitBug]:
    """
    Find bugs based on issues using the given filter function.

    Args:
        project_name: name of the project to draw the commit history from
        suspect_filter_function: function that creates and filters bugs

    Returns:
        the set of bugs created by the given filter
    """
    filtered_bugs = set()

    # IDENTIFY SUSPECTS
    suspect_tuples: tp.Set[PygitSuspectTuple] = set()
    for issue_event in issue_events:
        suspect_tuple = _find_corresponding_pygit_suspect_tuple(
            project_name, issue_event
        )
        if suspect_tuple:
            suspect_tuples.add(suspect_tuple)

    # CLASSIFY SUSPECTS
    for suspect_tuple in suspect_tuples:
        for suspect in suspect_tuple.consume_uncleared_suspects():
            partial_fix = False
            weak_suspect = False

            # partial fix?
            for other_tuple in suspect_tuples:
                if suspect.id == other_tuple.fixing_commit.id:
                    partial_fix = True
                    break

            # weak suspect?
            if not partial_fix:
                for other_tuple in suspect_tuples:
                    if suspect.id in [ns.id for ns in other_tuple.non_suspects]:
                        weak_suspect = True
                        break

            if partial_fix or weak_suspect:
                suspect_tuple.clear_suspect(suspect)

        pygit_bug = suspect_filter_function(suspect_tuple)
        if pygit_bug:
            filtered_bugs.add(pygit_bug)

    return frozenset(filtered_bugs)


def _filter_commit_message_bugs(
    project_name: str,
    commit_filter_function: tp.Callable[[pygit2.Repository, pygit2.Commit],
                                        tp.Optional[PygitBug]]
) -> tp.FrozenSet[PygitBug]:
    """
    Find bugs based on commit messages using the given filter function.

    Args:
        project_name: name of the project to draw the commit history from
        commit_filter_function: function that creates and filters bugs

    Returns:
        the set of bugs created by the given filter
    """
    filtered_bugs = set()
    project_repo = get_local_project_git(project_name)

    for commit in project_repo.walk(
        project_repo.head.target, pygit2.GIT_SORT_TIME
    ):
        pybug = commit_filter_function(project_repo, commit)
        if pybug:
            filtered_bugs.add(pybug)

    return frozenset(filtered_bugs)


def find_issue_bugs(
    project_name: str,
    fixing_commit: tp.Optional[str] = None,
    introducing_commit: tp.Optional[str] = None
) -> tp.FrozenSet[PygitBug]:
    """
    Find bugs in a project using github issues.

    Args:
        project_name: name of the project to search for bugs
        fixing_commit: if given, only return bugs that are fixed by that commit
        introducing_commit: if given, only return bugs that are (partially)
                            introduced by this commit

    Returns:
        a set of the selected bugs in the project
    """

    def accept_suspect_with_certain_introduction(
        suspect: PygitSuspectTuple
    ) -> tp.Optional[PygitBug]:
        bug = suspect.create_corresponding_bug()

        if fixing_commit and bug.fixing_commit.hex != fixing_commit:
            return None

        if introducing_commit and introducing_commit not in [
            str(fix.id) for fix in bug.introducing_commits
        ]:
            return None

        return bug

    return _filter_issue_bugs(
        project_name, _get_all_issue_events(project_name),
        accept_suspect_with_certain_introduction
    )


def find_commit_message_bugs(
    project_name: str,
    fixing_commit: tp.Optional[str] = None,
    introducing_commit: tp.Optional[str] = None
) -> tp.FrozenSet[PygitBug]:
    """
    Find bugs in a project based on the commit messages of the fixes.

    Args:
        project_name: name of the project to search for bugs
        fixing_commit: if given, only return bugs that are fixed by that commit
        introducing_commit: if given, only return bugs that are (partially)
                            introduced by this commit

    Returns:
        a set of the selected bugs in the project
    """

    def accept_commit_message_pybug(
        repo: pygit2.Repository, commit: pygit2.Commit
    ) -> tp.Optional[PygitBug]:
        if _is_closing_message(commit.message):
            bug = _create_corresponding_bug(commit, repo)

            if fixing_commit and bug.fixing_commit.hex != fixing_commit:
                return None

            if introducing_commit and introducing_commit not in [
                str(fix.id) for fix in bug.introducing_commits
            ]:
                return None

            return bug
        return None

    return _filter_commit_message_bugs(
        project_name, accept_commit_message_pybug
    )

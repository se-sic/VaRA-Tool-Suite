"""Bug Classes used by bug_provider."""

import typing as tp

import pygit2


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


def find_all_pygit_bugs(project_name: str) -> tp.FrozenSet[PygitBug]:
    """
    Creates a set of all bugs.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of PygitBugs.
    """
    pygit_bugs: tp.Set[PygitBug] = set()

    # TODO implement

    return frozenset(pygit_bugs)


def find_all_raw_bugs(project_name: str) -> tp.FrozenSet[RawBug]:
    """
    Creates a set of all bugs.

    Args:
        project_name: Name of the project in which to search for bugs

    Returns:
        A set of RawBugs.
    """
    hash_bugs: tp.Set[RawBug] = set()

    # TODO implement

    return frozenset(hash_bugs)


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
    # TODO implement

    return frozenset()


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
    # TODO implement

    return frozenset()


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
    # TODO implement

    return frozenset()


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
    # TODO implement

    return frozenset()

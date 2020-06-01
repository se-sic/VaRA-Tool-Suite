"""Bug Classes used by bug_provider."""

import typing as tp

import pygit2


class PygitBug:
    """Bug representation using the ``pygit2.Commit`` class."""

    def __init__(
        self, fixing_commit: pygit2.Commit,
        introducing_commits: tp.List[pygit2.Commit]
    ) -> None:
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = introducing_commits

    @property
    def fixing_commit(self) -> pygit2.Commit:
        """Commit fixing the bug as pygit2 Commit."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.List[pygit2.Commit]:
        """Commits introducing the bug as List of pygit2 Commits."""
        return self.__introducing_commits


class HashBug:
    """Bug representation using the Commit Hashes as Strings."""

    def __init__(self, fixing_commit: str, introducing_commits: tp.List[str]):
        self.__fixing_commit = fixing_commit
        self.__introducing_commits = introducing_commits

    @property
    def fixing_commit(self) -> str:
        """Hash of the commit fixing the bug as string."""
        return self.__fixing_commit

    @property
    def introducing_commits(self) -> tp.List[str]:
        """Hashes of the commits introducing the bug as List of strings."""
        return self.__introducing_commits


def find_all_pygit_bugs() -> tp.FrozenSet[PygitBug]:
    """
    Create a set of all bugs.

    :return:
        A set of PygitBug Objects.
    """
    pygit_bugs: tp.Set[PygitBug] = set()

    # TODO implement

    return frozenset(pygit_bugs)


def find_all_hash_bugs() -> tp.FrozenSet[HashBug]:
    """
    Create a set of all bugs.

    :return:
        A set of HashBug Objects.
    """
    hash_bugs: tp.Set[HashBug] = set()

    # TODO implement

    return frozenset(hash_bugs)


def find_pygit_bug_by_fix(fixing_commit: str) -> tp.Optional[PygitBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    :param fixing_commit:
        Commit Hash of the potentially fixing commit
    :return:
        A PygitBug Object, if there is such a bug
        None, if there is no such bug
    """
    # TODO implement

    return None


def find_hash_bug_by_fix(fixing_commit: str) -> tp.Optional[HashBug]:
    """
    Find the bug associated to some fixing commit, if there is any.

    :param fixing_commit:
        Commit Hash of the potentially fixing commit
    :return:
        A HashBug Object, if there is such a bug
        None, if there is no such bug
    """
    # TODO implement

    return None


def find_pygit_bug_by_introduction(
    introducing_commit: str
) -> tp.List[PygitBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    :param introducing_commit:
        Commit Hash of the introducing commit to look for
    :return:
        A list of PygitBug Objects
    """
    # TODO implement

    return []


def find_hash_bug_by_introduction(introducing_commit: str) -> tp.List[HashBug]:
    """
    Create a (potentially empty) list of bugs introduced by a certain commit.

    :param introducing_commit:
        Commit Hash of the introducing commit to look for
    :return:
        A list of HashBug Objects
    """
    # TODO implement

    return []

"""Utility module for BenchBuild project handling."""
import abc
import typing as tp
from enum import IntFlag
from pathlib import Path

import benchbuild as bb
import plumbum as pb
import pygit2
from benchbuild.source import Git
from benchbuild.source.base import target_prefix
from benchbuild.utils.cmd import cp, find, git, mkdir
from plumbum import local


def get_project_cls_by_name(project_name: str) -> tp.Type[bb.Project]:
    """Look up a BenchBuild project by it's name."""
    for proj in bb.project.ProjectRegistry.projects:
        if proj.endswith('gentoo') or proj.endswith("benchbuild"):
            # currently we only support vara provided projects
            continue

        if proj.startswith(project_name):
            project: tp.Type[bb.Project
                            ] = bb.project.ProjectRegistry.projects[proj]
            return project

    raise LookupError


def get_primary_project_source(project_name: str) -> bb.source.BaseSource:
    project_cls = get_project_cls_by_name(project_name)
    return bb.source.primary(*project_cls.SOURCE)


def get_local_project_git_path(project_name: str) -> Path:
    """Get the path to the local download location of git repository for a given
    benchbuild project."""
    primary_source = get_primary_project_source(project_name)
    if hasattr(primary_source, "fetch"):
        primary_source.fetch()

    return Path(target_prefix() + "/" + primary_source.local)


def get_local_project_git(project_name: str) -> pygit2.Repository:
    """Get the git repository for a given benchbuild project."""
    git_path = get_local_project_git_path(project_name)
    repo_path = pygit2.discover_repository(str(git_path))
    return pygit2.Repository(repo_path)


def get_tagged_commits(project_name: str) -> tp.List[tp.Tuple[str, str]]:
    """Get a list of all tagged commits along with their respective tags."""
    repo_loc = get_local_project_git_path(project_name)
    with local.cwd(repo_loc):
        # --dereference resolves tag IDs into commits
        # These lines are indicated by the suffix '^{}' (see man git-show-ref)
        ref_list: tp.List[str] = git("show-ref", "--tags",
                                     "--dereference").strip().split("\n")
        ref_list = [ref for ref in ref_list if ref.endswith("^{}")]
        refs: tp.List[tp.Tuple[str, str]] = [
            (ref_split[0], ref_split[1][10:-3])
            for ref_split in [ref.strip().split() for ref in ref_list]
        ]
        return refs


def get_all_revisions_between(c_start: str,
                              c_end: str,
                              short: bool = False) -> tp.List[str]:
    """
    Returns a list of all revisions between two commits c_start and c_end
    (inclusive), where c_start comes before c_end.

    It is assumed that the current working directory is the git repository.

    Args:
        c_start: first commit of the range
        c_end: last commit of the range
        short: shorten revision hashes
    """
    result = [c_start]
    result.extend(
        git(
            "log", "--pretty=%H", "--ancestry-path",
            "{}..{}".format(c_start, c_end)
        ).strip().split()
    )
    return list(map(lambda rev: rev[:10], result)) if short else result


class ProjectBinaryWrapper():
    """
    Wraps project binaries which get generated during compilation.

    >>> ProjectBinaryWrapper("binary_name", "path/to/binary")
    (binary_name: path/to/binary)
    """

    def __init__(self, binary_name: str, path_to_binary: Path) -> None:
        self.__binary_name = binary_name
        self.__binary_path = path_to_binary

    @property
    def name(self) -> str:
        return self.__binary_name

    @property
    def path(self) -> Path:
        return self.__binary_path

    def __str__(self) -> str:
        return f"{self.name}: {self.path}"

    def __repr__(self) -> str:
        return f"({str(self)})"


def wrap_paths_to_binaries_with_name(
    binaries: tp.List[tp.Tuple[str, str]]
) -> tp.List[ProjectBinaryWrapper]:
    """
    Generates a wrapper for project binaries.

    >>> wrap_paths_to_binaries_with_name([("fooer", "src/foo")])
    [(fooer: src/foo)]

    >>> wrap_paths_to_binaries_with_name([("fooer", "src/foo"), \
                                          ("barer", "src/bar")])
    [(fooer: src/foo), (barer: src/bar)]
    """
    return [ProjectBinaryWrapper(x[0], Path(x[1])) for x in binaries]


def wrap_paths_to_binaries(
    binaries: tp.List[str]
) -> tp.List[ProjectBinaryWrapper]:
    """
    Generates a wrapper for project binaries.

    >>> wrap_paths_to_binaries(["src/foo"])
    [(foo: src/foo)]

    >>> wrap_paths_to_binaries(["src/foo.so"])
    [(foo: src/foo.so)]

    >>> wrap_paths_to_binaries(["src/foo", "src/bar"])
    [(foo: src/foo), (bar: src/bar)]
    """
    return wrap_paths_to_binaries_with_name([(Path(x).stem, x) for x in binaries
                                            ])


class AbstractRevisionBlocker(abc.ABC):
    """A set of revisions that is marked as blocked."""

    def __init__(self, reason: tp.Optional[str] = None):
        self.__reason = reason

    @property
    def reason(self) -> tp.Optional[str]:
        """The reason for this block."""
        return self.__reason

    @abc.abstractmethod
    def __iter__(self) -> tp.Iterator[str]:
        pass

    def init_cache(self, project: str) -> None:
        """Subclasses relying on complex functionality for determining their set
        of blocked revisions can use this method to initialize a cache."""


class BlockedRevision(AbstractRevisionBlocker):
    """A single blocked revision."""

    def __init__(self, rev_id: str, reason: tp.Optional[str] = None):
        super().__init__(reason)
        self.__id = rev_id

    def __iter__(self) -> tp.Iterator[str]:
        return [self.__id].__iter__()


class BlockedRevisionRange(AbstractRevisionBlocker):
    """A range of blocked revisions."""

    def __init__(
        self, id_start: str, id_end: str, reason: tp.Optional[str] = None
    ):
        super().__init__(reason)
        self.__id_start = id_start
        self.__id_end = id_end
        # cache for commit hashes
        self.__revision_list: tp.Optional[tp.List[str]] = None

    def init_cache(self, project: str) -> None:
        self.__revision_list = get_all_revisions_between(
            self.__id_start, self.__id_end
        )

    def __iter__(self) -> tp.Iterator[str]:
        if self.__revision_list is None:
            raise AssertionError
        return self.__revision_list.__iter__()


class BugAndFixPair(AbstractRevisionBlocker):
    """A set of revisions containing a certain buggy commit but not its fix."""

    def __init__(
        self, id_bug: str, id_fix: str, reason: tp.Optional[str] = None
    ):
        super().__init__(reason)
        self.__id_bug = id_bug
        self.__id_fix = id_fix
        # cache for commit hashes
        self.__revision_list: tp.Optional[tp.List[str]] = None

    def init_cache(self, project: str) -> None:
        self.__revision_list = []
        repo = get_local_project_git(project)

        def get_identical_commits(rev_id: str) -> tp.List[str]:
            """Returns commits that are identical (same diff) to the given
            commit."""
            marked_revs = git("--no-pager", "log", "--cherry-mark",
                              rev_id).strip().split("\n")
            identical_ids = []
            for row in marked_revs:
                split = row.split(" ")
                if split[0] == "=":
                    identical_ids.append(split[1])
            return identical_ids

        class CommitState(IntFlag):
            BOT = 0
            FIXED = 1
            BUGGY = 2
            UNKNOWN = FIXED | BUGGY

        def find_blocked_commits(
            commit: pygit2.Commit, good: tp.List[pygit2.Commit],
            bad: tp.List[pygit2.Commit]
        ) -> tp.List[pygit2.Commit]:
            """
            Find all buggy commits not yet fixed by performing a backwards
            search starting at commit.

            Args:
                commit: the head commit
                good:   good commits (or fixes)
                bad:    bad commits (or bugs)

            Returns: all transitive parents of commit that have an ancestor
                     from bad that is not fixed by some commit from good.
            """
            stack: tp.List[pygit2.Commit] = [commit]
            blocked: tp.Dict[pygit2.Commit, CommitState] = {}

            while stack:
                current_commit = stack.pop()

                if current_commit in good:
                    blocked[current_commit] = CommitState.FIXED
                if current_commit in bad:
                    blocked[current_commit] = CommitState.BUGGY

                # must be deeper in the stack than its parents
                if current_commit not in blocked.keys():
                    stack.append(current_commit)

                for parent in current_commit.parents:
                    if parent not in blocked.keys():
                        stack.append(parent)

                # if all parents are already handled, determine whether
                # the current commit is blocked or not.
                if current_commit not in blocked.keys() and all(
                    parent in blocked.keys()
                    for parent in current_commit.parents
                ):
                    blocked[current_commit] = CommitState.BOT
                    for parent in current_commit.parents:
                        if blocked[parent] & CommitState.FIXED:
                            blocked[current_commit] |= CommitState.FIXED
                        if blocked[parent] & CommitState.BUGGY:
                            blocked[current_commit] |= CommitState.BUGGY

            return [
                commit for commit in blocked
                # for more aggressive blocking use:
                # if blocked[commit] & CommitState.BUGGY
                if blocked[commit] == CommitState.BUGGY
            ]

        # handle cases where commits are cherry-picked or similar
        bug_ids: tp.List[str] = [
            self.__id_bug, *get_identical_commits(self.__id_bug)
        ]
        bug_commits = [repo.get(bug_id) for bug_id in bug_ids]
        fix_ids: tp.List[str] = [
            self.__id_fix, *get_identical_commits(self.__id_fix)
        ]
        fix_commits = [repo.get(fix_id) for fix_id in fix_ids]

        # start search from all branch heads
        heads = git("show-ref", "--heads", "-s").strip().split("\n")
        for head in heads:
            self.__revision_list.extend([
                str(commit.id) for commit in
                find_blocked_commits(repo.get(head), fix_commits, bug_commits)
            ])

    def __iter__(self) -> tp.Iterator[str]:
        if self.__revision_list is None:
            raise AssertionError
        return self.__revision_list.__iter__()


def block_revisions(blocks: tp.List[AbstractRevisionBlocker]) -> tp.Any:
    """
    Decorator for project classes for blacklisting/blocking revisions.

    ATTENTION: This decorator depends on things introduced by the
    @with_git decorator and therefore must be used above that decorator.

    This adds a new static method ``is_blocked_revision`` that checks
    whether a given revision id is marked as blocked.

    Args:
        blocks: A list of ``BlockedRevision``'s and ``BlockedRevisionRange``'s.
    """

    def revision_blocker_decorator(cls: tp.Any) -> tp.Any:

        def is_blocked_revision_impl(
            rev_id: str
        ) -> tp.Tuple[bool, tp.Optional[str]]:
            """
            Checks whether a revision is blocked or not.

            Also returns the reason for the block if available.
            """
            # trigger caching for BlockedRevisionRanges
            if not cls.blocked_revisions_initialized:
                cls.blocked_revisions_initialized = True
                with local.cwd(get_local_project_git_path(cls.NAME)):
                    for block in blocks:
                        block.init_cache(cls.NAME)

            for b_entry in blocks:
                for b_item in b_entry:
                    if b_item.startswith(rev_id):
                        return True, b_entry.reason
            return False, None

        cls.blocked_revisions_initialized = False
        cls.is_blocked_revision = is_blocked_revision_impl
        return cls

    return revision_blocker_decorator


# ignore type as we do not have appropriate type information from benchbuild
class VaraTestRepoSource(Git):  # type: ignore
    """A project source for repositories stored in the vara-test-repos
    repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-passau/vara-test-repos",
        local="vara_test_repos",
        refspec="HEAD",
        limit=1
    )

    def fetch(self) -> pb.LocalPath:
        """
        Overrides ``Git``s fetch to
          1. fetch the vara-test-repos repo
          2. extract the specified repo from the vara-test-repos repo

        Returns:
            the path where the inner repo is extracted to
        """
        vara_test_repos_path = self.__vara_test_repos_git.fetch()

        # .gitted repo lies at vara_test_repos_path / self.remote
        # check out as self.local
        src_path = vara_test_repos_path / self.remote
        tgt_path = local.path(target_prefix()) / self.local

        mkdir("-p", tgt_path)
        cp("-r", src_path + "/.", tgt_path)

        with local.cwd(tgt_path):
            find(
                ".", "-depth", "-name", ".gitted", "-execdir", "mv", "-i", "{}",
                ".git", ";"
            )
            find(
                ".", "-name", "gitmodules", "-execdir", "mv", "-i", "{}",
                ".gitmodules", ";"
            )
            find(
                ".", "-name", "gitattributes", "-execdir", "mv", "-i", "{}",
                ".gitattributes", ";"
            )
            find(
                ".", "-name", "gitignore", "-execdir", "mv", "-i", "{}",
                ".gitignore", ";"
            )

        return tgt_path

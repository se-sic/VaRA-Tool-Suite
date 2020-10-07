"""Utility module for BenchBuild project handling."""
import typing as tp
from enum import Enum
from pathlib import Path

import benchbuild as bb
import plumbum as pb
import pygit2
from benchbuild.source import Git
from benchbuild.source.base import target_prefix
from benchbuild.utils.cmd import cp, find, git, mkdir
from plumbum import local


def get_project_cls_by_name(
    project_name: str
) -> tp.Type[bb.Project]:  # type: ignore
    """Look up a BenchBuild project by it's name."""
    for proj in bb.project.ProjectRegistry.projects:
        if proj.endswith('gentoo') or proj.endswith("benchbuild"):
            # currently we only support vara provided projects
            continue

        if proj.startswith(project_name):
            project: tp.Type[bb.Project  # type: ignore
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


class BinaryType(Enum):
    """Enum for different binary types."""
    value: int

    executable = 1
    shared_library = 2
    static_library = 3

    def __str__(self) -> str:
        return str(self.name)


class ProjectBinaryWrapper():
    """
    Wraps project binaries which get generated during compilation.

    >>> ProjectBinaryWrapper("binary_name", "path/to/binary", \
                             BinaryType.executable)
    (binary_name: path/to/binary | executable)
    """

    def __init__(
        self, binary_name: str, path_to_binary: Path, binary_type: BinaryType
    ) -> None:
        self.__binary_name = binary_name
        self.__binary_path = path_to_binary
        self.__type = binary_type

    @property
    def name(self) -> str:
        return self.__binary_name

    @property
    def path(self) -> Path:
        return self.__binary_path

    @property
    def type(self) -> BinaryType:
        return self.__type

    def __str__(self) -> str:
        return f"{self.name}: {self.path} | {str(self.type)}"

    def __repr__(self) -> str:
        return f"({str(self)})"


def wrap_paths_to_binaries_with_name(
    binaries: tp.List[tp.Tuple[str, str, BinaryType]]
) -> tp.List[ProjectBinaryWrapper]:
    """
    Generates a wrapper for project binaries.

    >>> wrap_paths_to_binaries_with_name([("fooer", "src/foo", \
                                           BinaryType.executable)])
    [(fooer: src/foo | executable)]

    >>> wrap_paths_to_binaries_with_name([("fooer", "src/foo", \
                                           BinaryType.executable), \
                                          ("barer", "src/bar", \
                                           BinaryType.shared_library)])
    [(fooer: src/foo | executable), (barer: src/bar | shared_library)]
    """
    return [ProjectBinaryWrapper(x[0], Path(x[1]), x[2]) for x in binaries]


def wrap_paths_to_binaries(
    binaries: tp.List[tp.Tuple[str, BinaryType]]
) -> tp.List[ProjectBinaryWrapper]:
    """
    Generates a wrapper for project binaries.

    >>> wrap_paths_to_binaries([("src/foo", BinaryType.executable)])
    [(foo: src/foo | executable)]

    >>> wrap_paths_to_binaries([("src/foo.so", BinaryType.shared_library)])
    [(foo: src/foo.so | shared_library)]

    >>> wrap_paths_to_binaries([("src/foo", BinaryType.static_library), \
                                ("src/bar",BinaryType.executable)])
    [(foo: src/foo | static_library), (bar: src/bar | executable)]
    """
    return wrap_paths_to_binaries_with_name([
        (Path(x[0]).stem, x[0], x[1]) for x in binaries
    ])


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
        Overrides ``Git`` s fetch to
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

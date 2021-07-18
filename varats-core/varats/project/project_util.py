"""Utility module for BenchBuild project handling."""
import logging
import os
import typing as tp
from distutils.dir_util import copy_tree
from enum import Enum
from pathlib import Path

import benchbuild as bb
import plumbum as pb
import pygit2
from benchbuild.source import Git, GitSubmodule
from benchbuild.source.base import target_prefix
from benchbuild.utils.cmd import git, mkdir, cp
from plumbum import local

LOG = logging.getLogger(__name__)


class CompilationError(Exception):
    """Exception raised if an error during the compilation was discovered."""


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


def get_primary_project_source(project_name: str) -> bb.source.FetchableSource:
    project_cls = get_project_cls_by_name(project_name)
    return bb.source.primary(*project_cls.SOURCE)


def get_local_project_git_path(
    project_name: str, git_name: tp.Optional[str] = None
) -> Path:
    """
    Get the path to the local download location of a git repository for a given
    benchbuild project.

    Args:
        project_name: name of the given benchbuild project
        git_name: name of the git repository, i.e., the name of the repository
                  folder. If no git_name is provided, the name of the primary
                  source is used.

    Returns:
        Path to the local download location of the git repository.
    """

    if git_name:
        source = get_extended_commit_lookup_source(project_name, git_name)
    else:
        source = get_primary_project_source(project_name)

    if is_git_source(source):
        source.fetch()

    return Path(target_prefix()) / Path(source.local)


def get_extended_commit_lookup_source(
    project_name: str, git_name: str
) -> bb.source.FetchableSource:
    """
    Get benchbuild FetchableSource specified by the git_name or raise a
    LookupError if no match was found within the given benchbuild project.

    Args:
        project_name: name of the given benchbuild project
        git_name: name of the git repository

    Returns:
        benchbuild FetchableSource of the searched git repository
    """

    project_cls = get_project_cls_by_name(project_name)
    for source in project_cls.SOURCE:
        if git_name == os.path.basename(source.local):
            return source

    raise LookupError(
        f"The specified git_name {git_name} could not be found in the sources"
    )


def get_local_project_git(
    project_name: str, git_name: tp.Optional[str] = None
) -> pygit2.Repository:
    """
    Get the git repository for a given benchbuild project.

    Args:
        project_name: name of the given benchbuild project
        git_name: name of the git repository

    Returns:
        git repository that matches the given git_name.
    """
    git_path = get_local_project_git_path(project_name, git_name)
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


def is_git_source(source: bb.source.FetchableSource) -> bool:
    """
    Checks if given base source is a git source.

    Args:
        source: base source to check

    Returns:
        true if the base source is a git source, false ow.
    """
    return hasattr(source, "fetch")


class BinaryType(Enum):
    """Enum for different binary types."""
    value: int  # pylint: disable=invalid-name

    EXECUTABLE = 1
    SHARED_LIBRARY = 2
    STATIC_LIBRARY = 3

    def __str__(self) -> str:
        return str(self.name.lower())


class ProjectBinaryWrapper():
    """
    Wraps project binaries which get generated during compilation.

    >>> ProjectBinaryWrapper("binary_name", "path/to/binary", \
                             BinaryType.EXECUTABLE)
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
        """Name of the binary."""
        return self.__binary_name

    @property
    def path(self) -> Path:
        """Path to the binary location."""
        return self.__binary_path

    @property
    def type(self) -> BinaryType:
        """Specifies the type, e.g., executable, shared, or static library, of
        the binary."""
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
                                           BinaryType.EXECUTABLE)])
    [(fooer: src/foo | executable)]

    >>> wrap_paths_to_binaries_with_name([("fooer", "src/foo", \
                                           BinaryType.EXECUTABLE), \
                                          ("barer", "src/bar", \
                                           BinaryType.SHARED_LIBRARY)])
    [(fooer: src/foo | executable), (barer: src/bar | shared_library)]
    """
    return [ProjectBinaryWrapper(x[0], Path(x[1]), x[2]) for x in binaries]


def wrap_paths_to_binaries(
    binaries: tp.List[tp.Tuple[str, BinaryType]]
) -> tp.List[ProjectBinaryWrapper]:
    """
    Generates a wrapper for project binaries, automatically infering the binary
    name.

    >>> wrap_paths_to_binaries([("src/foo", BinaryType.EXECUTABLE)])
    [(foo: src/foo | executable)]

    >>> wrap_paths_to_binaries([("src/foo.so", BinaryType.SHARED_LIBRARY)])
    [(foo: src/foo.so | shared_library)]

    >>> wrap_paths_to_binaries([("src/foo", BinaryType.STATIC_LIBRARY), \
                                ("src/bar",BinaryType.EXECUTABLE)])
    [(foo: src/foo | static_library), (bar: src/bar | executable)]
    """
    return wrap_paths_to_binaries_with_name([
        (Path(x[0]).stem, x[0], x[1]) for x in binaries
    ])


class BinaryNotFound(CompilationError):
    """Exception raised if an binary that should exist was not found."""

    @staticmethod
    def create_error_for_binary(
        binary: ProjectBinaryWrapper
    ) -> 'BinaryNotFound':
        """
        Creates a BinaryNotFound error for a specific binary.

        Args:
            binary: project binary that was not found

        Returns:
            initialzied BinaryNotFound error
        """
        msg = str(
            f"Could not find specified binary {binary.name} at relative " +
            f"project path: {str(binary.path)}"
        )
        return BinaryNotFound(msg)


def verify_binaries(project: bb.Project) -> None:
    """Verifies that all binaries for a given project exist."""
    for binary in project.binaries:
        if not binary.path.exists():
            raise BinaryNotFound.create_error_for_binary(binary)


def copy_renamed_git_to_dest(src_dir: Path, dest_dir: Path) -> None:
    """
    Renames git files that were made git_storable (e.g., .gitted) back to their
    original git name and stores the renamed copy at the destination path. The
    original files stay untouched. Renaming and copying will be skipped if the
    dest_dir already exists.

    Args:
        src_dir: path to the source directory
        dest_dir: path to the destination directory
    """
    if os.path.isdir(dest_dir):
        LOG.error(
            "The passed destination directory already exists. "
            "Copy/rename actions are skipped."
        )
        return
    copy_tree(str(src_dir), str(dest_dir))

    for root, dirs, files in os.walk(dest_dir, topdown=False):
        for name in files:
            if name == "gitmodules":
                os.rename(
                    os.path.join(root, name), os.path.join(root, ".gitmodules")
                )
            elif name == "gitattributes":
                os.rename(
                    os.path.join(root, name),
                    os.path.join(root, ".gitattributes")
                )
            elif name == "gitignore":
                os.rename(
                    os.path.join(root, name), os.path.join(root, ".gitignore")
                )
            elif name == ".gitted":
                os.rename(os.path.join(root, name), os.path.join(root, ".git"))

        for name in dirs:
            if name == ".gitted":
                os.rename(os.path.join(root, name), os.path.join(root, ".git"))


# TODO (se-passau/VaRA#717): Remove pylint's disable when issue is fixed
class VaraTestRepoSubmodule(GitSubmodule):  # type: ignore  # pylint: disable=R0901;
    """A project source for submodule repositories stored in the vara-test-repos
    repository."""

    __vara_test_repos_git = Git(
        remote="https://github.com/se-passau/vara-test-repos",
        local="vara_test_repos",
        refspec="HEAD",
        limit=1
    )

    def fetch(self) -> pb.LocalPath:
        """
        Overrides ``GitSubmodule`` s fetch to
          1. fetch the vara-test-repos repo
          2. extract the specified submodule from the vara-test-repos repo
          3. rename files that were made git_storable (e.g., .gitted) back to
             their original name (e.g., .git)

        Returns:
            the path where the inner repo is extracted to
        """
        self.__vara_test_repos_git.shallow = self.shallow
        self.__vara_test_repos_git.clone = self.clone

        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        submodule_path = vara_test_repos_path / Path(self.remote)
        submodule_target = local.path(target_prefix()) / Path(self.local)

        # Extract submodule
        if not os.path.isdir(submodule_target):
            copy_renamed_git_to_dest(submodule_path, submodule_target)

        return submodule_target


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
          3. rename files that were made git_storable (e.g., .gitted) back to
             their original name (e.g., .git)

        Returns:
            the path where the inner repo is extracted to
        """
        self.__vara_test_repos_git.shallow = self.shallow
        self.__vara_test_repos_git.clone = self.clone

        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        main_src_path = vara_test_repos_path / self.remote
        main_tgt_path = local.path(target_prefix()) / self.local

        # Extract main repository
        if not os.path.isdir(main_tgt_path):
            copy_renamed_git_to_dest(main_src_path, main_tgt_path)

        return main_tgt_path

    def version(self, target_dir: str, version: str = 'HEAD') -> pb.LocalPath:
        """Overrides ``Git`` s version to create a new git worktree pointing to
        the requested version."""

        main_repo_src_local = self.fetch()
        tgt_loc = pb.local.path(target_dir) / self.local
        vara_test_repos_path = self.__vara_test_repos_git.fetch()
        main_repo_src_remote = vara_test_repos_path / self.remote

        mkdir('-p', tgt_loc)

        # Extract main repository
        cp("-r", main_repo_src_local + "/.", tgt_loc)

        # Skip submodule extraction if none exist
        if not Path(tgt_loc / ".gitmodules").exists():
            with pb.local.cwd(tgt_loc):
                git("checkout", "--detach", version)
            return tgt_loc

        # Extract submodules
        with pb.local.cwd(tgt_loc):

            # Get submodule entries
            submodule_url_entry_list = git(
                "config", "--file", ".gitmodules", "--name-only",
                "--get-regexp", "url"
            ).split('\n')

            # Remove empty strings
            submodule_url_entry_list = list(
                filter(None, submodule_url_entry_list)
            )

            for entry in submodule_url_entry_list:
                relative_submodule_url = Path(
                    git("config", "--file", ".gitmodules", "--get",
                        entry).replace('\n', '')
                )
                copy_renamed_git_to_dest(
                    main_repo_src_remote / relative_submodule_url,
                    relative_submodule_url
                )
            git("checkout", "--detach", version)
            git("submodule", "update")

        return tgt_loc

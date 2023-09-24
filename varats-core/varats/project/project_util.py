"""Utility module for BenchBuild project handling."""
import logging
import os
import typing as tp
from enum import Enum
from pathlib import Path

import benchbuild as bb
import pygit2
from benchbuild.source import Git
from benchbuild.utils.cmd import git
from plumbum import local
from plumbum.commands.base import BoundCommand

from varats.utils.settings import bb_cfg

LOG = logging.getLogger(__name__)


class CompilationError(Exception):
    """Exception raised if an error during the compilation was discovered."""


def get_project_cls_by_name(project_name: str) -> tp.Type[bb.Project]:
    """Look up a BenchBuild project by its name."""
    from varats.project.varats_project import VProject  # pylint: disable=W0611
    for project_cls in bb.project.ProjectRegistry.projects.itervalues(
        prefix=project_name
    ):
        if not issubclass(project_cls, VProject):
            # currently we only support varats provided projects
            continue

        return tp.cast(tp.Type[bb.Project], project_cls)

    raise LookupError


def get_loaded_vara_projects() -> tp.Generator[tp.Type[bb.Project], None, None]:
    """Get all loaded vara projects."""
    from varats.project.varats_project import VProject  # pylint: disable=W0611
    for project_cls in bb.project.ProjectRegistry.projects.values():
        if not issubclass(project_cls, VProject):
            # currently we only support varats provided projects
            continue

        yield project_cls


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

    if not is_git_source(source):
        raise AssertionError(f"Project {project_name} does not use git.")

    base = Path(str(bb_cfg()["tmp_dir"]))
    git_path: Path = base / source.local
    if not git_path.exists():
        git_path = base / source.local.replace(os.sep, "-")
    if not git_path.exists():
        git_path = Path(source.fetch())
    return git_path


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


def get_local_project_gits(
    project_name: str
) -> tp.Dict[str, pygit2.Repository]:
    """
    Get the all git repositories for a given benchbuild project.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        dict with the git repositories for the project's sources
    """
    repos: tp.Dict[str, pygit2.Repository] = {}
    project_cls = get_project_cls_by_name(project_name)

    for source in project_cls.SOURCE:
        if isinstance(source, Git):
            source_name = os.path.basename(source.local)
            repos[source_name] = get_local_project_git(
                project_name, source_name
            )

    return repos


def get_local_project_git_paths(project_name: str) -> tp.Dict[str, Path]:
    """
    Get the all paths to the git repositories for a given benchbuild project.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        dict with the paths to the git repositories for the project's sources
    """
    repos: tp.Dict[str, Path] = {}
    project_cls = get_project_cls_by_name(project_name)

    for source in project_cls.SOURCE:
        if isinstance(source, Git):
            source_name = os.path.basename(source.local)
            repos[source_name] = get_local_project_git_path(
                project_name, source_name
            )

    return repos


def get_tagged_commits(project_name: str) -> tp.List[tp.Tuple[str, str]]:
    """Get a list of all tagged commits along with their respective tags."""
    repo_loc = get_local_project_git_path(project_name)
    with local.cwd(repo_loc):
        # --dereference resolves tag IDs into commits for annotated tags
        # These lines are indicated by the suffix '^{}' (see man git-show-ref)
        ref_list: tp.List[str] = git("show-ref", "--tags",
                                     "--dereference").strip().split("\n")

        # Only keep dereferenced or leightweight tags (i.e., only keep commits)
        # and strip suffix, if necessary
        refs: tp.List[tp.Tuple[str, str]] = [
            (ref_split[0], ref_split[1][10:].replace('^{}', ''))
            for ref_split in [ref.strip().split() for ref in ref_list]
            if git("cat-file", "-t", ref_split[1][10:]).replace('\n', ''
                                                               ) == 'commit'
        ]

        return refs


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

    @property
    def is_library(self) -> bool:
        return self in (BinaryType.SHARED_LIBRARY, BinaryType.STATIC_LIBRARY)

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
        self,
        binary_name: str,
        path_to_binary: Path,
        binary_type: BinaryType,
        entry_point: tp.Optional[Path] = None,
        valid_exit_codes: tp.Optional[tp.List[int]] = None,
    ) -> None:
        self.__binary_name = binary_name
        self.__binary_path = path_to_binary
        self.__type = binary_type

        if valid_exit_codes is not None:
            self.__valid_exit_codes = valid_exit_codes
        else:
            self.__valid_exit_codes = [0]

        if binary_type is BinaryType.EXECUTABLE:
            self.__entry_point = entry_point
            if not self.entry_point:
                self.__entry_point = self.path
        else:
            self.__entry_point = None

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

    @property
    def entry_point(self) -> tp.Optional[Path]:
        """Entry point to an executable "thing" that executes the wrapped
        binary, if possible."""
        return self.__entry_point

    @property
    def valid_exit_codes(self) -> tp.List[int]:
        """Specifies which exit codes indicate a successful execution of the
        binary."""
        return self.__valid_exit_codes

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        if self.type is not BinaryType.EXECUTABLE:
            LOG.warning(f"Executing {self.type} is not possible.")
            return None

        executable_entry_point = local[f"{self.entry_point}"]
        return executable_entry_point(*args, **kwargs)

    def __getitem__(self, args: tp.Any) -> BoundCommand:
        if self.type is not BinaryType.EXECUTABLE:
            raise AssertionError(f"Executing {self.type} is not possible.")

        executable_entry_point = local[f"{self.entry_point}"]
        return executable_entry_point[args]

    def __str__(self) -> str:
        return f"{self.name}: {self.path} | {str(self.type)}"

    def __repr__(self) -> str:
        return f"({str(self)})"


class BinaryNotFound(CompilationError):
    """Exception raised if a binary that should exist was not found."""

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
    # pylint: disable=import-outside-toplevel
    from distutils.dir_util import copy_tree
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

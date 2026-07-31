"""Utility module for BenchBuild project handling."""

import logging
import os
import typing as tp
from _operator import attrgetter
from collections import defaultdict
from enum import Enum
from itertools import chain
from pathlib import Path

import benchbuild as bb
import pygit2
from benchbuild.source import Git
from plumbum import local
from plumbum.commands.base import BoundCommand

if tp.TYPE_CHECKING:
    from benchbuild.utils.revision_ranges import AbstractRevisionRange

from varats.utils.git_util import (
    CommitHash,
    CommitLookupTy,
    CommitRepoPair,
    FullCommitHash,
    RepositoryHandle,
    ShortCommitHash,
    calc_repo_loc,
    get_authors,
    get_submodule_commits,
    num_commits,
)
from varats.utils.settings import bb_cfg

LOG = logging.getLogger(__name__)


class CompilationError(Exception):
    """Exception raised if an error during the compilation was discovered."""


def get_project_cls_by_name(project_name: str) -> type[bb.Project]:
    """Look up a BenchBuild project by its name."""
    from varats.project.varats_project import VProject  # noqa

    for project_cls in bb.project.ProjectRegistry.projects.itervalues(
        prefix=project_name
    ):
        if not issubclass(project_cls, VProject):
            # currently we only support varats provided projects
            continue

        return tp.cast("type[bb.Project]", project_cls)

    raise LookupError


def get_loaded_vara_projects() -> tp.Generator[type[bb.Project], None, None]:
    """Get all loaded VaRA projects."""
    from varats.project.varats_project import VProject  # noqa

    for project_cls in bb.project.ProjectRegistry.projects.values():
        if not issubclass(project_cls, VProject):
            # currently we only support varats provided projects
            continue

        yield project_cls


def get_primary_project_source(project_name: str) -> bb.source.FetchableSource:
    """Get the primary source for the given project."""
    project_cls = get_project_cls_by_name(project_name)
    return bb.source.primary(*project_cls.SOURCE)


def get_local_project_repo(
    project_name: str, git_name: str | None = None
) -> RepositoryHandle:
    """Get the repo handle for the given project and optional repo name."""
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
    return RepositoryHandle(git_path)


def get_local_project_repos(project_name: str) -> dict[str, RepositoryHandle]:
    """
    Get the all git repositories for a given benchbuild project.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        dict with the repository handles for the project's git sources
    """
    repos: dict[str, RepositoryHandle] = {}
    project_cls = get_project_cls_by_name(project_name)

    for source in project_cls.SOURCE:
        if isinstance(source, Git):
            source_name = Path(source.local).name
            repos[source_name] = get_local_project_repo(
                project_name, source_name
            )

    return repos


def get_extended_commit_lookup_source(
    project_name: str, git_name: str
) -> bb.source.FetchableSource:
    """
    Get benchbuild FetchableSource specified by the git_name.

    Raises a LookupError if no match was found within the given project.

    Args:
        project_name: name of the given benchbuild project
        git_name: name of the git repository

    Returns:
        benchbuild FetchableSource of the searched git repository
    """
    project_cls = get_project_cls_by_name(project_name)
    for source in project_cls.SOURCE:
        if git_name == Path(source.local).name:
            return source

    raise LookupError(
        f"The specified git_name {git_name} could not be found in the sources"
    )


def create_project_commit_lookup_helper(project_name: str) -> CommitLookupTy:
    """
    Creates a commit lookup function for project repositories.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        a Callable that maps a commit hash and repository name to the
        corresponding commit.
    """
    repos = get_local_project_repos(project_name)

    def get_commit(crp: CommitRepoPair) -> pygit2.Commit:
        """
        Gets the commit from a given ``CommitRepoPair``.

        Args:
            crp: the ``CommitRepoPair`` for the commit to get

        Returns:
            the commit corresponding to the given CommitRepoPair
        """
        commit = repos[crp.repository_name].maybe_pygit_commit(crp.commit_hash)
        if not commit:
            raise LookupError(
                f"Could not find commit {crp} for project {project_name}."
            )

        return commit

    return get_commit


def get_tagged_commits(project_name: str) -> list[tuple[str, str]]:
    """Get a list of all tagged commits along with their respective tags."""
    repo = get_local_project_repo(project_name)
    # --dereference resolves tag IDs into commits for annotated tags
    # These lines are indicated by the suffix '^{}' (see man git-show-ref)
    ref_list: list[str] = (
        repo("show-ref", "--tags", "--dereference").strip().split("\n")
    )

    # Only keep dereferenced or leightweight tags (i.e., only keep commits)
    # and strip suffix, if necessary
    refs: list[tuple[str, str]] = [
        (ref_split[0], ref_split[1][10:].replace('^{}', ''))
        for ref_split in [ref.strip().split() for ref in ref_list]
        if repo("cat-file", "-t", ref_split[1][10:]).replace('\n', '')
        == 'commit'
    ]

    return refs


def num_project_commits(project_name: str, revision: FullCommitHash) -> int:
    """
    Calculate the number of commits of a project including submodules.

    Args:
        project_name: name of the project to calculate commits for
        revision: revision to calculate commits at

    Returns:
        the number of commits in the project
    """
    project_repos = get_local_project_repos(project_name)
    main_repo = get_local_project_repo(project_name)

    commits = num_commits(main_repo, revision.hash)
    for submodule, sub_rev in get_submodule_commits(
        main_repo, revision.hash
    ).items():
        if submodule not in project_repos:
            LOG.warning(
                "Ignoring unknown submodule %s",
            )
            continue
        commits += num_commits(project_repos[submodule], sub_rev.hash)
    return commits


def num_project_authors(project_name: str, revision: FullCommitHash) -> int:
    """
    Calculate the number of authors of a project including submodules.

    Args:
        project_name: name of the project to calculate authors for
        revision: revision to authors commits at

    Returns:
        the number of authors in the project
    """
    project_repos = get_local_project_repos(project_name)
    main_repo = get_local_project_repo(project_name)

    authors = get_authors(main_repo, revision.hash)
    for submodule, sub_rev in get_submodule_commits(
        main_repo, revision.hash
    ).items():
        if submodule not in project_repos:
            LOG.warning("Ignoring unknown submodule %s", submodule)
            continue
        authors.update(get_authors(project_repos[submodule], sub_rev.hash))
    return len(authors)


def calc_project_loc(project_name: str, revision: FullCommitHash) -> int:
    """
    Calculate the LOC for a project including submodules at the given revision.

    Args:
        project_name: name of the project to calculate LOC for
        revision: revision to calculate LOC at

    Returns:
        the LOC in the project
    """
    project_repos = get_local_project_repos(project_name)
    main_repo = get_local_project_repo(project_name)

    loc = calc_repo_loc(main_repo, revision.hash)
    for submodule, sub_rev in get_submodule_commits(
        main_repo, revision.hash
    ).items():
        if submodule not in project_repos:
            LOG.warning("Ignoring unknown submodule %s", submodule)
            continue
        loc += calc_repo_loc(project_repos[submodule], sub_rev.hash)
    return loc


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
        """Returns whether the binary type is considered a libraary."""
        return self in (BinaryType.SHARED_LIBRARY, BinaryType.STATIC_LIBRARY)

    def __str__(self) -> str:
        """Return binary type as string."""
        return str(self.name.lower())


class ProjectBinaryWrapper:
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
        entry_point: Path | None = None,
        valid_exit_codes: list[int] | None = None,
    ) -> None:
        """Crates a binary wrapper."""
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
        """The type of a binary (executable, shared, or static library)."""
        return self.__type

    @property
    def entry_point(self) -> Path | None:
        """
        Entry point for a binary.

        The entry point can be the binary itself, but also a script that
        calls the actual binary.
        """
        return self.__entry_point

    @property
    def valid_exit_codes(self) -> list[int]:
        """Specifies exit codes for a successful execution of the binary."""
        return self.__valid_exit_codes

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        """Execute the binary with the given arguments."""
        if self.type is not BinaryType.EXECUTABLE:
            LOG.warning(f"Executing {self.type} is not possible.")
            return None

        executable_entry_point = local[f"{self.entry_point}"]
        return executable_entry_point(*args, **kwargs)

    def __getitem__(self, args: tp.Any) -> BoundCommand:
        """Build a command for the binary with the given arguments."""
        if self.type is not BinaryType.EXECUTABLE:
            raise AssertionError(f"Executing {self.type} is not possible.")

        executable_entry_point = local[f"{self.entry_point}"]
        return executable_entry_point[args]

    def __str__(self) -> str:
        """Return binary as string."""
        return f"{self.name}: {self.path} | {self.type!s}"

    def __repr__(self) -> str:
        """Return representation of the binary."""
        return f"({self!s})"


class BinaryNotFoundError(CompilationError):
    """Exception raised if a binary that should exist was not found."""

    @staticmethod
    def create_error_for_binary(
        binary: ProjectBinaryWrapper,
    ) -> 'BinaryNotFoundError':
        """
        Creates a BinaryNotFound error for a specific binary.

        Args:
            binary: project binary that was not found

        Returns:
            initialzied BinaryNotFound error
        """
        msg = str(
            f"Could not find specified binary {binary.name} at relative "
            + f"project path: {binary.path!s}"
        )
        return BinaryNotFoundError(msg)


def verify_binaries(project: bb.Project) -> None:
    """Verifies that all binaries for a given project exist."""
    for binary in project.binaries:
        if not binary.path.exists():
            raise BinaryNotFoundError.create_error_for_binary(binary)


class RevisionBinaryMap(tp.Container[str]):
    """A map that specifies for which revision ranges a binary is valid."""

    def __init__(self, repo: RepositoryHandle) -> None:
        """Creates a RevisionBinaryMap."""
        self.__repo_location = repo.worktree_path
        self.__revision_specific_mappings: dict[
            AbstractRevisionRange, list[ProjectBinaryWrapper]
        ] = defaultdict(list)
        self.__always_valid_mappings: list[ProjectBinaryWrapper] = []

    def specify_binary(
        self, location: str, binary_type: BinaryType, **kwargs: tp.Any
    ) -> 'RevisionBinaryMap':
        """
        Add a binary to the map.

        Args:
            location: where the binary can be found, relative to the
                      project-source root
            binary_type: the type of binary that is produced
            override_binary_name: overrides the used binary name
            override_entry_point: overrides the executable entry point
            only_valid_in: additionally specifies a validity range that
                           specifies in which revision range this binary is
                           produced

        Returns:
            self for builder-style usage
        """
        binary_location_path = Path(location)
        binary_name: str = kwargs.get(
            "override_binary_name", binary_location_path.stem
        )
        override_entry_point = kwargs.get("override_entry_point")
        if override_entry_point:
            override_entry_point = Path(override_entry_point)
        validity_range: AbstractRevisionRange | None = kwargs.get(
            "only_valid_in"
        )
        valid_exit_codes = kwargs.get("valid_exit_codes")

        wrapped_binary = ProjectBinaryWrapper(
            binary_name,
            binary_location_path,
            binary_type,
            override_entry_point,
            valid_exit_codes,
        )

        if validity_range:
            validity_range.init_cache(str(self.__repo_location))
            self.__revision_specific_mappings[validity_range].append(
                wrapped_binary
            )
        else:
            self.__always_valid_mappings.append(wrapped_binary)

        return self

    def __getitem__(self, revision: CommitHash) -> list[ProjectBinaryWrapper]:
        """Get the binaries available for a given revision."""
        revision = revision.to_short_commit_hash()
        revision_specific_binaries = []

        for (
            validity_range,
            wrapped_binaries,
        ) in self.__revision_specific_mappings.items():
            if revision in map(ShortCommitHash, validity_range):
                revision_specific_binaries.extend(wrapped_binaries)

        revision_specific_binaries.extend(self.__always_valid_mappings)

        return sorted(
            revision_specific_binaries, key=attrgetter("name", "path")
        )

    def __contains__(self, binary_name: object) -> bool:
        """Checks whether the map contains a given binary."""
        if isinstance(binary_name, str):
            for binary in chain(
                self.__always_valid_mappings,
                *self.__revision_specific_mappings.values(),
            ):
                if binary.name == binary_name:
                    return True

        return False


def copy_renamed_git_to_dest(src_dir: Path, dest_dir: Path) -> None:
    """
    Restores .gitted repositories.

    Renames git files that were made git_storable (e.g., .gitted) back to their
    original git name and stores the renamed copy at the destination path. The
    original files stay untouched. Renaming and copying will be skipped if the
    dest_dir already exists.

    Args:
        src_dir: path to the source directory
        dest_dir: path to the destination directory
    """
    from shutil import copytree  # noqa

    if Path.is_dir(dest_dir):
        LOG.error(
            "The passed destination directory already exists. "
            "Copy/rename actions are skipped."
        )
        return
    copytree(str(src_dir), str(dest_dir))

    for root, dirs, files in os.walk(dest_dir, topdown=False):
        root_path = Path(root)
        for name in files:
            if name == "gitmodules":
                Path.rename(root_path / name, root_path / ".gitmodules")
            elif name == "gitattributes":
                Path.rename(
                    root_path / name,
                    root_path / ".gitattributes",
                )
            elif name == "gitignore":
                Path.rename(root_path / name, root_path / ".gitignore")
            elif name == ".gitted":
                Path.rename(root_path / name, root_path / ".git")

        for name in dirs:
            if name == ".gitted":
                Path.rename(root_path / name, root_path / ".git")

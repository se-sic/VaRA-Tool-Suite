"""Commit map module."""

import logging
import typing as tp
from collections.abc import ItemsView
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir
from plumbum import local
from pygtrie import CharTrie

from varats.project.project_util import (
    get_local_project_git_path,
    get_primary_project_source,
)
from varats.utils.git_util import (
    get_current_branch,
    FullCommitHash,
    ShortCommitHash,
)

LOG = logging.getLogger(__name__)


class AmbiguousCommitHash(Exception):
    """Raised if an ambiguous commit hash is encountered."""


class CommitMap():
    """Provides a mapping from commit hash to additional information."""

    def __init__(self, stream: tp.Iterable[str]) -> None:
        self.__hash_to_id: CharTrie = CharTrie()
        for line in stream:
            slices = line.strip().split(', ')
            self.__hash_to_id[slices[1]] = int(slices[0])

    def convert_to_full_or_warn(
        self, short_commit: ShortCommitHash
    ) -> FullCommitHash:
        """
        Warn if a short-form commit hash is ambiguous.

        Args:
            short_commit: the short-form commit hash to complete

        Returns:
            a full-length commit hash that starts with the short-form hash
        """
        full_commits = self.complete_c_hash(short_commit)
        if len(full_commits) > 1:
            LOG.warning(f"Short commit hash is ambiguous: {short_commit.hash}.")
        return next(iter(full_commits))

    def convert_to_full_or_raise(
        self, short_commit: ShortCommitHash
    ) -> FullCommitHash:
        """
        Raise an exception if a short-form commit hash is ambiguous.

        Args:
            short_commit: the short-form commit hash to complete

        Returns:
            a full-length commit hash that starts with the short-form hash
        """
        full_commits = self.complete_c_hash(short_commit)
        if len(full_commits):
            raise AmbiguousCommitHash
        return next(iter(full_commits))

    def time_id(self, c_hash: FullCommitHash) -> int:
        """
        Convert a commit hash to a time id that allows a total order on the
        commits, based on the c_map, e.g., created from the analyzed git
        history.

        Args:
            c_hash: commit hash

        Returns:
            unique time-ordered id
        """
        return tp.cast(int, self.__hash_to_id[c_hash.hash])

    def short_time_id(self, c_hash: ShortCommitHash) -> int:
        """
        Convert a short commit hash to a time id that allows a total order on
        the commits, based on the c_map, e.g., created from the analyzed git
        history.

        The first time id is returned where the hash belonging to it starts
        with the short hash.

        Args:
            c_hash: commit hash

        Returns:
            unique time-ordered id
        """
        return self.time_id(self.convert_to_full_or_warn(c_hash))

    def c_hash(self, time_id: int) -> FullCommitHash:
        """
        Get the hash belonging to the time id.

        Args:
            time_id: unique time-ordered id

        Returns:
            commit hash
        """
        for c_hash, t_id in self.__hash_to_id.items():
            if t_id == time_id:
                return FullCommitHash(tp.cast(str, c_hash))
        raise KeyError

    def complete_c_hash(
        self, short_commit: ShortCommitHash
    ) -> tp.Set[FullCommitHash]:
        """
        Get a set of all commit hashes that start with a given short-form hash.

        Args:
            short_commit: the short-form commit hash to complete

        Returns:
            a set of full-length commit hashes that start with the short-form
            commit hash
        """
        subtrie = self.__hash_to_id.items(prefix=short_commit.hash)
        if subtrie:
            return {FullCommitHash(c_hash) for c_hash, _ in subtrie}
        raise KeyError

    def mapping_items(self) -> tp.ItemsView[str, int]:
        """Get an iterator over the mapping items."""
        return ItemsView(self.__hash_to_id)

    def write_to_file(self, target_file: tp.TextIO) -> None:
        """
        Write commit map to a file.

        Args:
            target_file: needs to be a writable stream, i.e., support .write()
        """
        for item in self.__hash_to_id.items():
            target_file.write(f"{item[1]}, {item[0]}\n")

    def __str__(self) -> str:
        return str(self.__hash_to_id)


def generate_commit_map(
    path: Path,
    end: str = "HEAD",
    start: tp.Optional[str] = None,
    refspec: str = "HEAD"
) -> CommitMap:
    """
    Generate a commit map for a repository including the commits.

    Range of commits that get included in the map: `]start..end]`

    Args:
        path: to the repository
        end: last commit that should be included
        start: parent of the first commit that should be included
        refspec: that should be checked out

    Returns: initalized ``CommitMap``
    """
    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        old_head = get_current_branch()
        git("checkout", refspec)
        full_out = git("--no-pager", "log", "--pretty=format:'%H'")
        wanted_out = git(
            "--no-pager", "log", "--pretty=format:'%H'", search_range
        )

        def format_stream() -> tp.Generator[str, None, None]:
            wanted_cm = set()
            for line in wanted_out.split('\n'):
                wanted_cm.add(line[1:-1])

            for number, line in enumerate(reversed(full_out.split('\n'))):
                line = line[1:-1]
                if line in wanted_cm:
                    yield f"{number}, {line}\n"

        git("checkout", old_head)
        return CommitMap(format_stream())


def store_commit_map(cmap: CommitMap, output_file_path: str) -> None:
    """Store commit map to file."""
    mkdir("-p", Path(output_file_path).parent)

    with open(output_file_path, "w") as c_map_file:
        cmap.write_to_file(c_map_file)


def load_commit_map_from_path(cmap_path: Path) -> CommitMap:
    """Load a commit map from a given `.cmap` file path."""
    with open(cmap_path, "r") as c_map_file:
        return CommitMap(c_map_file.readlines())


def get_commit_map(
    project_name: str,
    cmap_path: tp.Optional[Path] = None,
    end: str = "HEAD",
    start: tp.Optional[str] = None
) -> CommitMap:
    """
    Get a commit map for a project.

    Range of commits that get included in the map: `]start..end]`

    Args:
        project_name: name of the project
        cmap_path: path to a existing commit map file
        end: last commit that should be included in the map
        start: commit before the first commit that should be included in the map

    Returns: a bidirectional commit map from commits to time IDs
    """
    if cmap_path is None:
        project_git_path = get_local_project_git_path(project_name)
        primary_source = get_primary_project_source(project_name)
        refspec = "HEAD"
        if hasattr(primary_source, "refspec"):
            refspec = primary_source.refspec

        return generate_commit_map(project_git_path, end, start, refspec)

    return load_commit_map_from_path(cmap_path)


def create_lazy_commit_map_loader(
    project_name: str,
    cmap_path: tp.Optional[Path] = None,
    end: str = "HEAD",
    start: tp.Optional[str] = None
) -> tp.Callable[[], CommitMap]:
    """
    Create a generator function that lazy loads a CommitMap.

    Range of commits that get included in the map: `]start..end]`

    Args:
        project_name: name of the project
        cmap_path: path to a existing commit map file
        end: last commit that should be included in the map
        start: commit before the first commit that should be included in the map

    Returns: a callable that creates a commit map on demand when called
    """
    lazy_cached_cmap = None

    def get_cmap_lazy() -> CommitMap:
        nonlocal lazy_cached_cmap
        if lazy_cached_cmap is None:
            lazy_cached_cmap = get_commit_map(
                project_name, cmap_path, end, start
            )

        return lazy_cached_cmap

    return get_cmap_lazy

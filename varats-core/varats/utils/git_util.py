"""Utility module for handling git repos."""
import abc
import os
import re
import typing as tp
from enum import Enum
from pathlib import Path

import pygit2
from benchbuild.utils.cmd import git
from plumbum import local

from varats.project.project_util import (
    get_local_project_git,
    get_primary_project_source,
)

if tp.TYPE_CHECKING:
    from varats.mapping.commit_map import CommitMap  # pylint: disable=W0611

_FULL_COMMIT_HASH_LENGTH = 40
_SHORT_COMMIT_HASH_LENGTH = 10


class CommitHash(abc.ABC):
    """Base class for commit hash abstractions."""

    def __init__(self, short_commit_hash: str):
        if not len(short_commit_hash) >= self.hash_length():
            raise ValueError("Commit hash too short")
        self.__commit_hash = short_commit_hash[:self.hash_length()]

    @property
    def hash(self) -> str:
        return self.__commit_hash

    @staticmethod
    @abc.abstractmethod
    def hash_length() -> int:
        """Required length of the CommitHash."""

    @staticmethod
    def from_pygit_commit(commit: pygit2.Commit) -> 'FullCommitHash':
        return FullCommitHash(str(commit.id))

    def __str__(self) -> str:
        return self.hash

    def __repr__(self) -> str:
        return self.hash

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, CommitHash):
            return self.hash == other.hash
        return False

    def __hash__(self) -> int:
        return hash(self.hash)


class ShortCommitHash(CommitHash):
    """Shortened commit hash."""

    @staticmethod
    def hash_length() -> int:
        return _SHORT_COMMIT_HASH_LENGTH


class FullCommitHash(CommitHash):
    """Full-length commit hash."""

    @staticmethod
    def hash_length() -> int:
        return _FULL_COMMIT_HASH_LENGTH

    @property
    def short_hash(self) -> str:
        """Abbreviated commit hash."""
        return self.hash[:_SHORT_COMMIT_HASH_LENGTH]

    def to_short_commit_hash(self) -> ShortCommitHash:
        return ShortCommitHash(self.hash)

    def startswith(self, short_hash: CommitHash) -> bool:
        return self.hash.startswith(short_hash.hash)


UNCOMMITTED_COMMIT_HASH = FullCommitHash(
    "0000000000000000000000000000000000000000"
)

CommitHashTy = tp.TypeVar("CommitHashTy", bound=CommitHash)
ShortCH = ShortCommitHash
FullCH = FullCommitHash


def commit_hashes_sorted_lexicographically(
    commit_hashes: tp.Iterable[CommitHashTy]
) -> tp.Iterable[CommitHashTy]:
    return sorted(commit_hashes, key=lambda x: x.hash)


def short_commit_hashes_sorted_by_time_id(
    commit_hashes: tp.Iterable[ShortCommitHash], commit_map: 'CommitMap'
) -> tp.Iterable[ShortCommitHash]:
    return sorted(commit_hashes, key=commit_map.short_time_id)


def full_commit_hashes_sorted_by_time_id(
    commit_hashes: tp.Iterable[FullCommitHash], commit_map: 'CommitMap'
) -> tp.Iterable[FullCommitHash]:
    return sorted(commit_hashes, key=commit_map.time_id)


################################################################################
# Git interaction helpers


def get_current_branch(repo_folder: tp.Optional[Path] = None) -> str:
    """
    Get the current branch of a repository, e.g., HEAD.

    Args:
        repo_folder: where the git repository is located

    Returns: branch name
    """
    if repo_folder is None or repo_folder == Path(''):
        return tp.cast(str, git("rev-parse", "--abbrev-ref", "HEAD").strip())

    with local.cwd(repo_folder):
        return tp.cast(str, git("rev-parse", "--abbrev-ref", "HEAD").strip())


################################################################################
# Git interaction classes


class ChurnConfig():
    """
    The churn config allows the user to change how code churn is calculated.

    Churn is by default calulcated considering all files in a repository. Users
    can select a specific set of file extensions to only be considered in the
    code churn, e.g., by selecting `h` and `c` only C related files will be used
    to compute the code churn.
    """

    class Language(Enum):
        """Enum for different languages that can be used to filter code
        churn."""
        value: tp.Set[str]  # pylint: disable=invalid-name

        C = {"h", "c"}
        CPP = {"h", "hxx", "hpp", "cxx", "cpp"}

    def __init__(self) -> None:
        self.__enabled_languages: tp.List[ChurnConfig.Language] = []

    @staticmethod
    def create_default_config() -> 'ChurnConfig':
        """Create a default configuration that includes all files in the code
        churn, e.g., enabling all languages/file extensions."""
        return ChurnConfig()

    @staticmethod
    def create_c_language_config() -> 'ChurnConfig':
        """Create a config that only allows C related files, e.g., headers and
        source files."""
        config = ChurnConfig()
        config.enable_language(ChurnConfig.Language.C)
        return config

    @staticmethod
    def create_c_style_languages_config() -> 'ChurnConfig':
        """Create a config that allows all files related to C-style languages,
        i.e., C/CPP."""
        config = ChurnConfig.create_c_language_config()
        config.enable_language(ChurnConfig.Language.CPP)
        return config

    @staticmethod
    def init_as_default_if_none(
        config: tp.Optional['ChurnConfig']
    ) -> 'ChurnConfig':
        """
        Returns a default initialized config or the passed one.

        Args:
            config: possibly initialized config

        Returns:
            passed `config` or a default initialized one
        """
        if config is None:
            return ChurnConfig.create_default_config()
        return config

    @property
    def include_everything(self) -> bool:
        """
        Checks if all files should be considered in the code churn.

        Returns:
            True, if no specific language is enabled
        """
        return not bool(self.__enabled_languages)

    @property
    def enabled_languages(self) -> tp.List['ChurnConfig.Language']:
        """Returns a list of specifically enabled languages."""
        return self.__enabled_languages

    def is_enabled(self, file_extension: str) -> bool:
        """
        Checks if a file_extension is enabled.

        Args:
            file_extension: extension of a file, e.g., `h` for foo.h

        Returns:
            True, if the extension is currently enabled in the config
        """
        for lang in self.enabled_languages:
            if file_extension in lang.value:
                return True
        return False

    def is_language_enabled(self, language: 'ChurnConfig.Language') -> bool:
        """
        Checks if a language is enabled.

        Args:
            language: language to check

        Returns:
            True, if the language was enabled
        """
        return language in self.enabled_languages

    def enable_language(self, language: 'ChurnConfig.Language') -> None:
        """Enable `language` in the config."""
        self.__enabled_languages.append(language)

    def disable_language(self, language: 'ChurnConfig.Language') -> None:
        """Disable `language` in the config."""
        self.__enabled_languages.remove(language)

    def get_extensions_repr(self,
                            prefix: str = "",
                            suffix: str = "") -> tp.List[str]:
        """
        Returns a list that contains all file extensions from all enabled
        languages extended with the passed pre-/suffix.

        Args:
            prefix: prefix adding to the strings head
            suffix: suffix adding to the strings tail

        Returns:
            list of modified string file extensions
        """
        extensions_list: tp.List[str] = []

        for ext in sorted({
            ext for lang in self.enabled_languages for ext in lang.value
        }):
            ext = prefix + ext + suffix
            extensions_list.append(ext)

        return extensions_list


CommitLookupTy = tp.Callable[[FullCommitHash, str], pygit2.Commit]


def create_commit_lookup_helper(project_name: str) -> CommitLookupTy:
    """
    Creates a commit lookup function for project repositories.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        a Callable that maps a commit hash and repository name to the
        corresponding commit.
    """

    # Only used when no git_name is provided
    primary_project_repo = get_local_project_git(project_name)
    primary_source_name = os.path.basename(
        get_primary_project_source(project_name).local
    )
    repos: tp.Dict[str, pygit2.Repository] = {}

    # Maps hash to commit within corresponding git_name
    cache_dict: tp.Dict[str, tp.Dict[FullCommitHash, pygit2.Commit]] = {}

    def get_commit(
        c_hash: FullCommitHash,
        git_name: tp.Optional[str] = None
    ) -> pygit2.Commit:
        """
        Gets the commit from a given commit hash within its corresponding
        repository name.

        Args:
            c_hash: commit hash of the searched commit
            git_name: name of the repository, wherein the commit is being
                      searched. If no git_name is provided, the name of the
                      primary source is used.


        Returns:
            commit, which corresponds to the given commit hash within the given
            repository.
        """

        if git_name == "Unknown":
            git_name = None

        if not git_name:
            if primary_source_name not in cache_dict:
                repos[primary_source_name] = primary_project_repo
                cache_dict[primary_source_name] = {}

            if c_hash in cache_dict[primary_source_name]:
                return cache_dict[primary_source_name][c_hash]

            commit = primary_project_repo.get(c_hash.hash)
            if commit is None:
                raise LookupError(
                    f"Could not find commit {c_hash} in {project_name}"
                )
            cache_dict[primary_source_name][c_hash] = commit
            return commit

        if git_name not in cache_dict:
            current_repo = get_local_project_git(project_name, git_name)
            repos[git_name] = current_repo
            cache_dict[git_name] = {}

        if c_hash in cache_dict[git_name]:
            return cache_dict[git_name][c_hash]

        commit = repos[git_name].get(c_hash)
        if commit is None:
            raise LookupError(
                f"Could not find commit {c_hash} in "
                f"project {project_name} within git repository {git_name}"
            )
        cache_dict[git_name][c_hash] = commit
        return commit

    return get_commit


class CommitRepoPair():
    """Pair of a commit hash and the name of the repository it is based in."""

    def __init__(self, commit_hash: FullCommitHash, repo_name: str) -> None:
        self.__commit_hash = commit_hash
        self.__repo_name = repo_name

    @property
    def commit_hash(self) -> FullCommitHash:
        return self.__commit_hash

    @property
    def repository_name(self) -> str:
        return self.__repo_name

    def __lt__(self, other: tp.Any) -> bool:
        if isinstance(other, CommitRepoPair):
            if self.commit_hash.hash == other.commit_hash.hash:
                return self.repository_name < other.repository_name
            return self.commit_hash.hash < other.commit_hash.hash
        return False

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, CommitRepoPair):
            return (
                self.commit_hash == other.commit_hash and
                self.repository_name == other.repository_name
            )
        return False

    def __hash__(self) -> int:
        return hash((self.commit_hash, self.repository_name))

    def __str__(self) -> str:
        return f"{self.repository_name}[{self.commit_hash}]"


MappedCommitResultType = tp.TypeVar("MappedCommitResultType")


def map_commits(
    func: tp.Callable[[pygit2.Commit], MappedCommitResultType],
    cr_pair_list: tp.Iterable[CommitRepoPair],
    commit_lookup: CommitLookupTy,
) -> tp.Sequence[MappedCommitResultType]:
    """Maps a function over a range of commits."""
    # Skip 0000 hashes that we added to mark uncommitted files
    return [
        func(commit_lookup(cr_pair.commit_hash, cr_pair.repository_name))
        for cr_pair in cr_pair_list
        if cr_pair.commit_hash != UNCOMMITTED_COMMIT_HASH
    ]


GIT_LOG_MATCHER = re.compile(
    r"\'(?P<hash>.*)\'\n?" + r"( (?P<files>\d*) files? changed)?" +
    r"(, (?P<insertions>\d*) insertions?\(\+\))?" +
    r"(, (?P<deletions>\d*) deletions?\(-\))?"
)
GIT_DIFF_MATCHER = re.compile(
    r"( (?P<files>\d*) files? changed)?" +
    r"(, (?P<insertions>\d*) insertions?\(\+\))?" +
    r"(, (?P<deletions>\d*) deletions?\(-\))?"
)


def __calc_code_churn_range_impl(
    repo_path: str,
    churn_config: ChurnConfig,
    start_range: tp.Optional[str] = None,
    end_range: tp.Optional[str] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range.

    [start..end]. If no range is supplied, the churn values of all commits are
    calculated.

    git log --pretty=format:'%H' --date=short --shortstat -- ':*.[enabled_exts]'

    Args:
        repo_path: path to the git repository
        churn_config: churn config to customize churn generation
        start_range: begin churn calculation at start commit
        end_range: end churn calculation at end commit
    """

    churn_values: tp.Dict[FullCommitHash, tp.Tuple[int, int, int]] = {}

    if start_range is None and end_range is None:
        revision_range = None
    elif start_range is None:
        revision_range = "..{}".format(end_range)
    elif end_range is None:
        revision_range = "{}~..".format(start_range)
    else:
        revision_range = "{}~..{}".format(start_range, end_range)

    repo_git = git["-C", repo_path]
    log_base_params = ["log", "--pretty=%H"]
    diff_base_params = [
        "log", "--pretty=format:'%H'", "--date=short", "--shortstat", "-l0"
    ]
    if revision_range:
        log_base_params.append(revision_range)
        diff_base_params.append(revision_range)

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    if revision_range:
        stdout = repo_git(diff_base_params)
        revs = repo_git(log_base_params).strip().split()
    else:
        stdout = repo_git(diff_base_params)
        revs = repo_git(log_base_params).strip().split()
    # initialize with 0 as otherwise commits without changes would be
    # missing from the churn data
    for rev in revs:
        churn_values[rev] = (0, 0, 0)
    for match in GIT_LOG_MATCHER.finditer(stdout):
        commit_hash = FullCommitHash(match.group('hash'))

        def value_or_zero(match_result: tp.Any) -> int:
            if match_result is not None:
                return int(match_result)
            return 0

        files_changed = value_or_zero(match.group('files'))
        insertions = value_or_zero(match.group('insertions'))
        deletions = value_or_zero(match.group('deletions'))
        churn_values[commit_hash] = (files_changed, insertions, deletions)

    return churn_values


def calc_code_churn_range(
    repo: tp.Union[pygit2.Repository, str],
    churn_config: tp.Optional[ChurnConfig] = None,
    start_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None,
    end_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range.

    [start..end]. If no range is supplied, the churn values of all commits are
    calculated.

    Args:
        repo: git repository
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return __calc_code_churn_range_impl(
        repo.path if isinstance(repo, pygit2.Repository) else repo,
        churn_config, start_range.id
        if isinstance(start_range, pygit2.Commit) else start_range,
        end_range.id if isinstance(end_range, pygit2.Commit) else end_range
    )


def calc_commit_code_churn(
    repo: pygit2.Repository,
    commit: pygit2.Commit,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Tuple[int, int, int]:
    """
    Calculates churn of a specific commit.

    Args:
        repo: git repository
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(repo, churn_config, commit, commit)[
        FullCommitHash.from_pygit_commit(commit)]


def calc_code_churn(
    repo: pygit2.Repository,
    commit_a: pygit2.Commit,
    commit_b: pygit2.Commit,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Tuple[int, int, int]:
    """
    Calculates churn between two commits.

    Args:
        repo: git repository
        commit_a: base commit for diff calculation
        commit_b: target commit for diff calculation
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    repo_git = git["-C", repo.path]
    diff_base_params = [
        "diff", "--shortstat", "-l0",
        str(commit_a.id),
        str(commit_b.id)
    ]

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    stdout = repo_git(diff_base_params)
    # initialize with 0 as otherwise commits without changes would be
    # missing from the churn data
    match = GIT_DIFF_MATCHER.match(stdout)
    if match:

        def value_or_zero(match_result: tp.Any) -> int:
            if match_result is not None:
                return int(match_result)
            return 0

        files_changed = value_or_zero(match.group('files'))
        insertions = value_or_zero(match.group('insertions'))
        deletions = value_or_zero(match.group('deletions'))
        return files_changed, insertions, deletions

    return 0, 0, 0


def calc_repo_code_churn(
    repo: pygit2.Repository,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates code churn for a repository.

    Args:
        repo: git repository
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(repo, churn_config)


def __print_calc_repo_code_churn(
    repo: pygit2.Repository,
    churn_config: tp.Optional[ChurnConfig] = None
) -> None:
    """Prints calc repo code churn data like git log would do."""
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    churn_map = calc_repo_code_churn(repo, churn_config)

    for commit in repo.walk(repo.head.target, pygit2.GIT_SORT_TIME):
        commit_hash = FullCommitHash.from_pygit_commit(commit)
        print(commit_hash)

        try:
            churn = churn_map[commit_hash]
        except KeyError:
            # ignore commits that are not related to code changes
            continue

        if churn[0] == 1:
            changed_files = " 1 file changed"
        else:
            changed_files = " {} files changed".format(churn[0])

        if churn[1] == 0:
            insertions = ""
        elif churn[1] == 1:
            insertions = ", 1 insertion(+)"
        else:
            insertions = ", {} insertions(+)".format(churn[1])

        if churn[2] == 0:
            deletions = ""
        elif churn[2] == 1:
            deletions = ", 1 deletion(-)"
        else:
            deletions = ", {} deletions(-)".format(churn[2])

        if churn[0] > 0 and churn[1] == 0 and churn[2] == 0:
            insertions = ", 0 insertions(+)"
            deletions = ", 0 deletions(-)"

        if churn[0] > 0:
            print(changed_files + insertions + deletions)
            print()

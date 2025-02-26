"""Utility module for handling git repos."""
import abc
import logging
import re
import typing as tp
from enum import Enum
from pathlib import Path
from types import TracebackType

import pygit2
from benchbuild.utils.cmd import git, grep
from plumbum import TF, RETCODE
from plumbum.commands.base import BoundCommand

from varats.utils.exceptions import unwrap

if tp.TYPE_CHECKING:
    from benchbuild.utils.revision_ranges import AbstractRevisionRange

    import varats.mapping.commit_map as cm  # pylint: disable=W0611

LOG = logging.Logger(__name__)

_FULL_COMMIT_HASH_LENGTH = 40
_SHORT_COMMIT_HASH_LENGTH = 10


class CommitHash(abc.ABC):
    """Base class for commit hash abstractions."""

    def __init__(self, short_commit_hash: str):
        if not len(short_commit_hash) >= self.hash_length():
            raise ValueError(
                f"Commit hash too short, only got {short_commit_hash}"
            )
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

    @abc.abstractmethod
    def to_short_commit_hash(self) -> 'ShortCommitHash':
        """Return the short form of the CommitHash."""

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

    def to_short_commit_hash(self) -> 'ShortCommitHash':
        return self

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
    commit_hashes: tp.Iterable[ShortCommitHash], commit_map: 'cm.CommitMap'
) -> tp.Iterable[ShortCommitHash]:
    return sorted(commit_hashes, key=commit_map.short_time_id)


def full_commit_hashes_sorted_by_time_id(
    commit_hashes: tp.Iterable[FullCommitHash], commit_map: 'cm.CommitMap'
) -> tp.Iterable[FullCommitHash]:
    return sorted(commit_hashes, key=commit_map.time_id)


################################################################################
# Git interaction helpers


class RepositoryHandle:
    """Wrapper class providing access to a git repository using either pygit2 or
    commandline-git."""

    def __init__(self, worktree_path: Path):
        self.__worktree_path = worktree_path
        self.__git: BoundCommand = git["-C", str(self.__worktree_path)]

        self.__repo_path: tp.Optional[Path] = None
        self.__libgit_repo: tp.Optional[pygit2.Repository] = None

    def __call__(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        """Call git with the given arguments."""
        return self.__git(*args, **kwargs)

    def __getitem__(self, *args: tp.Any) -> BoundCommand:
        """Get a bound git command with the given arguments."""
        return self.__git.bound_command(*args)

    @property
    def repo_name(self) -> str:
        """Name of the repository, i.e., name of the worktree folder."""
        return self.worktree_path.name

    @property
    def worktree_path(self) -> Path:
        """Path to the main worktree of the repository, typically the parent of
        the .git folder."""
        return self.__worktree_path

    @property
    def repo_path(self) -> Path:
        """Path to the git repository, i.e., the .git folder."""
        if self.__repo_path is None:
            self.__repo_path = Path(
                unwrap(
                    pygit2.discover_repository(str(self.worktree_path)),
                    f"No git repository found."
                )
            )

        return self.__repo_path

    @property
    def pygit_repo(self) -> pygit2.Repository:
        """A pygit2 repository instance for the repository."""
        if self.__libgit_repo is None:
            self.__libgit_repo = pygit2.Repository(str(self.repo_path))

        return self.__libgit_repo

    def __eq__(self, other: tp.Any) -> bool:
        if not isinstance(other, RepositoryHandle):
            return False
        return self.repo_path == other.repo_path

    def __repr__(self) -> str:
        return f"RepositoryHandle({self.repo_path})"

    def __str__(self) -> str:
        return self.repo_name


def is_commit_hash(value: str) -> bool:
    """
    Checks if a string is a valid git (sha1) hash.

    Args:
        value: to check
    """
    return re.search("^[a-fA-F0-9]{1,40}$", value) is not None


def get_current_branch(repo: RepositoryHandle) -> str:
    """
    Get the current branch of a repository, e.g., HEAD.

    Args:
        repo: git repository handle

    Returns: branch name
    """
    return tp.cast(str, repo("rev-parse", "--abbrev-ref", "HEAD").strip())


def get_head_commit(repo: RepositoryHandle) -> FullCommitHash:
    """
    Get the current HEAD commit.

    Args:
        repo: git repository handle

    Returns: head commit hash
    """
    return FullCommitHash(repo("rev-parse", "HEAD").strip())


def get_initial_commit(repo: RepositoryHandle) -> FullCommitHash:
    """
    Get the initial commit of a repository, i.e., the first commit made.

    Args:
        repo: git repository handle

    Returns: initial commit hash
    """
    return FullCommitHash(repo("rev-list", "--max-parents=0", "HEAD").strip())


def get_submodule_commits(repo: RepositoryHandle,
                          c_head: str = "HEAD") -> tp.Dict[str, FullCommitHash]:
    """
    Get the revisions of all submodules of a repo at a given commit.

    Args:
        repo: repository to get the submodules for
        c_head: the commit to look at

    Returns:
        a mapping from submodule name to commit
    """
    submodule_regex = re.compile(
        r"\d{6} commit (?P<hash>[\da-f]{40})\s+(?P<name>.+)$"
    )

    ls_tree_result = repo("ls-tree", c_head)
    result: tp.Dict[str, FullCommitHash] = {}
    for line in ls_tree_result.splitlines():
        match = submodule_regex.match(line)
        if match:
            result[match.group("name")] = FullCommitHash(match.group("hash"))
    return result


def get_all_revisions_between(
    repo: RepositoryHandle, c_start: str, c_end: str,
    hash_type: tp.Type[CommitHashTy]
) -> tp.List[CommitHashTy]:
    """
    Returns a list of all revisions between two commits c_start and c_end (both
    inclusive), where c_start comes before c_end.

    It is assumed that the current working directory is the git repository.

    Args:
        repo: git repository handle
        c_start: first commit of the range
        c_end: last commit of the range
        hash_type: type of the commit hash to return
    """
    result = [c_start]
    result.extend(
        reversed(
            repo(
                "log", "--pretty=%H", "--ancestry-path", f"{c_start}..{c_end}"
            ).strip().split()
        )
    )
    return list(map(hash_type, result))


def typed_revision_range(
    repo: RepositoryHandle, rev_range: 'AbstractRevisionRange',
    hash_type: tp.Type[CommitHashTy]
) -> tp.Iterator[CommitHashTy]:
    """
    Typed iterator for revision ranges.

    Args:
        repo: git repository handle
        rev_range: the revision range to iterate
        hash_type: the commit type to use for iteration

    Returns:
        an iterator over the typed commits in the range
    """
    rev_range.init_cache(str(repo.repo_path))
    for revision in rev_range:
        yield hash_type(revision)


def get_commits_before_timestamp(repo: RepositoryHandle,
                                 timestamp: str) -> tp.List[FullCommitHash]:
    """
    Get all commits before a specific timestamp (given as a git date format).

    Note: for imprecise timestamps (e.g., only 2020), the day and month will
    default to today.

    Args:
        repo: git repository handle
        timestamp: before which commits should be collected

    Returns: list[last_commit_before_timestamp, ..., initial_commits]
    """
    return [
        FullCommitHash(hash_val) for hash_val in
        repo("rev-list", f"--before={timestamp}", "HEAD").split()
    ]


def get_commits_after_timestamp(repo: RepositoryHandle,
                                timestamp: str) -> tp.List[FullCommitHash]:
    """
    Get all commits after a specific timestamp (given as a git date format).

        Note: for imprecise timestamps (e.g., only 2020), the day and month will
        default to today.

        Args:
            repo: git repository handle
            timestamp: after which commits should be collected

    Returns: list[newest_commit, ..., last_commit_after_timestamp]
    """
    return [
        FullCommitHash(hash_val)
        for hash_val in repo("rev-list", f"--after={timestamp}", "HEAD").split()
    ]


def contains_source_code(
    repo: RepositoryHandle,
    commit: ShortCommitHash,
    churn_config: tp.Optional['ChurnConfig'] = None
) -> bool:
    """
    Check if a commit contains source code of any language specified with the
    churn config.

    Args:
        repo: git repository handle
        commit: to check
        churn_config: to specify the files that should be considered

    Returns: True, if source code of a language, specified in the churn
        config, was found in the commit
    """
    if not churn_config:
        churn_config = ChurnConfig.create_c_style_languages_config()

    git_show_args = ["show", "--exit-code", "-m", "--quiet", commit.hash, "--"]
    git_show_args += churn_config.get_extensions_repr('*.')
    # There should be a '*' in front of 'git_show_args' to unpack the list.
    # However, yapf and sphinx are unable to parse this.
    # Fortunately, plumbum seems to unpack this correctly before running.
    # Still: fix when possible.
    return_code = repo[git_show_args] & RETCODE

    if return_code == 0:
        return False

    if return_code == 1:
        return True

    raise RuntimeError(f"git diff failed with retcode={return_code}")


def num_commits(repo: RepositoryHandle, c_start: str = "HEAD") -> int:
    """
    Count the commits in a git repo starting from the given commit back to the
    initial commit.

    Args:
        repo: git repository handle
        c_start: commit to start counting at

    Returns:
        the number of commits
    """
    return int(repo("rev-list", "--count", c_start))


def num_authors(repo: RepositoryHandle, c_start: str = "HEAD") -> int:
    """
    Count the authors in a git repo starting from the given commit back to the
    initial commit.

    Args:
        repo: git repository handle
        c_start: commit to start counting at

    Returns:
        the number of authors
    """
    return len(repo("shortlog", "-s", c_start).splitlines())


def get_authors(repo: RepositoryHandle, c_start: str = "HEAD") -> tp.Set[str]:
    """
    Get the authors in a git repo starting from the given commit back to the
    initial commit.

    Args:
        repo: git repository handle
        c_start: commit to start counting at

    Returns:
        the number of authors
    """
    author_regex = re.compile(r"\s*\d+\s+(?P<author>.+)$")

    lines = repo("shortlog", "-s", c_start).splitlines()
    result = set()
    for line in lines:
        match = author_regex.match(line)
        if match:
            result.add(match.group("author"))
    return result


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
        CPP = {"h", "hxx", "hpp", "cxx", "cpp", "cc"}

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

    def __repr__(self) -> str:
        return str(self)


def get_submodule_head(
    repo: RepositoryHandle, submodule: RepositoryHandle, commit: FullCommitHash
) -> FullCommitHash:
    """
    Retrieve the checked out commit for a submodule of a project.

    Args:
        repo: main project repository handle
        submodule: submodule repository handle
        commit: commit of the project's main repo

    Returns:
        checked out commit of the submodule
    """
    if submodule.repo_name == repo.repo_name:
        return commit

    submodule_status = repo("ls-tree", commit)
    commit_pattern = re.compile(
        r"[0-9]* commit ([0-9abcdef]*)\t" + submodule.repo_name
    )
    if match := commit_pattern.search(submodule_status):
        return FullCommitHash(match.group(1))

    raise AssertionError(f"Unknown submodule {submodule.repo_name}")


MappedCommitResultType = tp.TypeVar("MappedCommitResultType")
CommitLookupTy = tp.Callable[[CommitRepoPair], pygit2.Commit]


def map_commits(
    func: tp.Callable[[pygit2.Commit], MappedCommitResultType],
    cr_pair_list: tp.Iterable[CommitRepoPair],
    commit_lookup: CommitLookupTy,
) -> tp.Sequence[MappedCommitResultType]:
    """Maps a function over a range of commits."""
    # Skip 0000 hashes that we added to mark uncommitted files
    return [
        func(commit_lookup(cr_pair))
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
    repo: RepositoryHandle,
    churn_config: ChurnConfig,
    start_range: tp.Optional[FullCommitHash] = None,
    end_range: tp.Optional[FullCommitHash] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range.

    [start..end]. If no range is supplied, the churn values of all commits are
    calculated.

    git log --pretty=format:'%H' --date=short --shortstat -- ':*.[enabled_exts]'

    Args:
        repo: git repository handle
        churn_config: churn config to customize churn generation
        start_range: begin churn calculation at start commit
        end_range: end churn calculation at end commit
    """

    churn_values: tp.Dict[FullCommitHash, tp.Tuple[int, int, int]] = {}
    if start_range and start_range == get_initial_commit(repo):
        start_range = None

    if start_range is None and end_range is None:
        revision_range = None
    elif start_range is None:
        revision_range = f"{end_range.hash}"  # type: ignore
    elif end_range is None:
        revision_range = f"{start_range.hash}~.."
    else:
        revision_range = f"{start_range.hash}~..{end_range.hash}"

    log_base_params = ["log", "--pretty=%H"]
    diff_base_params = ["log", "--pretty=format:'%H'", "--shortstat", "-l0"]
    if revision_range:
        log_base_params.append(revision_range)
        diff_base_params.append(revision_range)

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    stdout = repo(diff_base_params)
    revs = repo(log_base_params).strip().split()

    # initialize with 0 as otherwise commits without changes would be
    # missing from the churn data
    for rev in revs:
        churn_values[FullCommitHash(rev)] = (0, 0, 0)
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
    repo: RepositoryHandle,
    churn_config: tp.Optional[ChurnConfig] = None,
    start_range: tp.Optional[FullCommitHash] = None,
    end_range: tp.Optional[FullCommitHash] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range.

    [start..end]. If no range is supplied, the churn values of all commits are
    calculated.

    Args:
        repo: git repository handle
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return __calc_code_churn_range_impl(
        repo, churn_config, start_range, end_range
    )


def calc_commit_code_churn(
    repo: RepositoryHandle,
    commit_hash: FullCommitHash,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Tuple[int, int, int]:
    """
    Calculates churn of a specific commit.

    Args:
        repo: git repository handle
        commit_hash: commit hash to get churn for
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(repo, churn_config, commit_hash,
                                 commit_hash)[commit_hash]


def calc_code_churn(
    repo: RepositoryHandle,
    commit_a: FullCommitHash,
    commit_b: FullCommitHash,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Tuple[int, int, int]:
    """
    Calculates churn between two commits.

    Args:
        repo: git repository handle
        commit_a: base commit for diff calculation
        commit_b: target commit for diff calculation
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    diff_base_params = [
        "diff", "--shortstat", "-l0", commit_a.hash, commit_b.hash
    ]

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    stdout = repo(*diff_base_params)
    # initialize with 0 as otherwise commits without changes would be
    # missing from the churn data
    if match := GIT_DIFF_MATCHER.match(stdout):

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
    repo: RepositoryHandle,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates code churn for a repository.

    Args:
        repo: git repository handle
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(repo, churn_config)


def __print_calc_repo_code_churn(
    repo: RepositoryHandle,
    churn_config: tp.Optional[ChurnConfig] = None
) -> None:
    """Prints calc repo code churn data like git log would do."""
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    churn_map = calc_repo_code_churn(repo, churn_config)

    for commit in repo.pygit_repo.walk(
        repo.pygit_repo.head.target, pygit2.GIT_SORT_TIME
    ):
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
            changed_files = f" {churn[0]} files changed"

        if churn[1] == 0:
            insertions = ""
        elif churn[1] == 1:
            insertions = ", 1 insertion(+)"
        else:
            insertions = f", {churn[1]} insertions(+)"

        if churn[2] == 0:
            deletions = ""
        elif churn[2] == 1:
            deletions = ", 1 deletion(-)"
        else:
            deletions = f", {churn[2]} deletions(-)"

        if churn[0] > 0 and churn[1] == 0 and churn[2] == 0:
            insertions = ", 0 insertions(+)"
            deletions = ", 0 deletions(-)"

        if churn[0] > 0:
            print(changed_files + insertions + deletions)
            print()


def calc_repo_loc(repo: RepositoryHandle, rev_range: str) -> int:
    """
    Calculate the LOC for a repository.

    Args:
        repo: handle for the repository to calculate the LOC for
        rev_range: the revision range to use for LOC calculation

    Returns:
        the number of lines in source-code files
    """
    churn_config = ChurnConfig.create_c_style_languages_config()
    file_pattern = re.compile(
        "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
    )

    loc: int = 0
    files = repo(
        "ls-tree",
        "-r",
        "--name-only",
        rev_range,
    ).splitlines()

    for file in files:
        if file_pattern.match(file):
            lines = repo("show", f"{rev_range}:{file}").splitlines()
            loc += len([line for line in lines if line])

    return loc


################################################################################
# Special git-specific classes


def has_branch(repo: RepositoryHandle, branch_name: str) -> bool:
    """Checks if a branch exists in the local repository."""

    exit_code = repo["rev-parse", "--verify", branch_name] & TF
    return tp.cast(bool, exit_code)


def has_remote_branch(
    repo: RepositoryHandle, branch_name: str, remote: str
) -> bool:
    """Checks if a remote branch of a repository exists."""
    exit_code = (
        repo["ls-remote", "--heads", remote, branch_name] | grep[branch_name]
    ) & RETCODE
    return tp.cast(bool, exit_code == 0)


def branch_has_upstream(
    repo: RepositoryHandle, branch_name: str, upstream: str = 'origin'
) -> bool:
    """Check if a branch has an upstream remote."""
    exit_code = (
        repo["rev-parse", "--abbrev-ref", branch_name + "@{upstream}"] |
        grep[upstream]
    ) & RETCODE
    return tp.cast(bool, exit_code == 0)


class RepositoryAtCommit():
    """Context manager to work with a repository at a specific revision, without
    duplicating the repository."""

    def __init__(
        self, repo: RepositoryHandle, revision: ShortCommitHash
    ) -> None:
        self.__repo = repo.pygit_repo
        self.__initial_head = self.__repo.head
        self.__revision = self.__repo.get(revision.hash)

    def __enter__(self) -> Path:
        self.__repo.checkout_tree(self.__revision)
        return Path(self.__repo.path).parent

    def __exit__(
        self, exc_type: tp.Optional[tp.Type[BaseException]],
        exc_value: tp.Optional[BaseException],
        exc_traceback: tp.Optional[TracebackType]
    ) -> None:
        self.__repo.checkout(self.__initial_head)

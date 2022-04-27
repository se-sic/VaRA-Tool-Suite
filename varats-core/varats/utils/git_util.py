"""Utility module for handling git repos."""
import abc
import re
import typing as tp
from enum import Enum
from itertools import chain
from pathlib import Path

import pygit2
from benchbuild.utils.cmd import git, grep
from benchbuild.utils.revision_ranges import RevisionRange
from plumbum import local, TF, RETCODE

from varats.project.project_util import (
    get_local_project_gits,
    get_primary_project_source,
    get_local_project_git_path,
    BinaryType,
    ProjectBinaryWrapper,
)

if tp.TYPE_CHECKING:
    import varats.mapping.commit_map as cm  # pylint: disable=W0611

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
    commit_hashes: tp.Iterable[ShortCommitHash], commit_map: 'cm.CommitMap'
) -> tp.Iterable[ShortCommitHash]:
    return sorted(commit_hashes, key=commit_map.short_time_id)


def full_commit_hashes_sorted_by_time_id(
    commit_hashes: tp.Iterable[FullCommitHash], commit_map: 'cm.CommitMap'
) -> tp.Iterable[FullCommitHash]:
    return sorted(commit_hashes, key=commit_map.time_id)


################################################################################
# Git interaction helpers


def is_commit_hash(value: str) -> bool:
    """
    Checks if a string is a valid git (sha1) hash.

    Args:
        value: to check
    """
    return re.search("^[a-fA-F0-9]{1,40}$", value) is not None


def __get_git_path_arg(repo_folder: tp.Optional[Path] = None) -> tp.List[str]:
    if repo_folder is None or repo_folder == Path(''):
        return []

    return ["-C", f"{repo_folder}"]


def get_current_branch(repo_folder: tp.Optional[Path] = None) -> str:
    """
    Get the current branch of a repository, e.g., HEAD.

    Args:
        repo_folder: where the git repository is located

    Returns: branch name
    """
    return tp.cast(
        str,
        git(
            __get_git_path_arg(repo_folder), "rev-parse", "--abbrev-ref", "HEAD"
        ).strip()
    )


def get_head_commit(repo_folder: tp.Optional[Path] = None) -> FullCommitHash:
    """
    Get the current HEAD commit.

    Args:
        repo_folder:where the git repository is located

    Returns: head commit hash
    """
    return FullCommitHash(
        git(__get_git_path_arg(repo_folder), "rev-parse", "HEAD").strip()
    )


def get_initial_commit(repo_folder: tp.Optional[Path] = None) -> FullCommitHash:
    """
    Get the initial commit of a repository, i.e., the first commit made.

    Args:
        repo_folder: where the git repository is located

    Returns: initial commit hash
    """
    return FullCommitHash(
        git(
            __get_git_path_arg(repo_folder), "rev-list", "--max-parents=0",
            "HEAD"
        ).strip()
    )


def get_all_revisions_between(
    c_start: str,
    c_end: str,
    hash_type: tp.Type[CommitHashTy],
    repo_folder: tp.Optional[Path] = None
) -> tp.List[CommitHashTy]:
    """
    Returns a list of all revisions between two commits c_start and c_end (both
    inclusive), where c_start comes before c_end.

    It is assumed that the current working directory is the git repository.

    Args:
        c_start: first commit of the range c_end: last commit of the range
        short: shorten revision hashes repo_folder: where the git repository is
        located
    """
    result = [c_start]
    result.extend(
        reversed(
            git(
                __get_git_path_arg(repo_folder), "log", "--pretty=%H",
                "--ancestry-path", f"{c_start}..{c_end}"
            ).strip().split()
        )
    )
    return list(map(hash_type, result))


def get_commits_before_timestamp(
    timestamp: str,
    repo_folder: tp.Optional[Path] = None
) -> tp.List[FullCommitHash]:
    """
    Get all commits before a specific timestamp (given as a git date format).

    Note: for imprecise timestamps (e.g., only 2020), the day and month will
    default to today.

    Args:
        timestamp: before which commits should be collected
        repo_folder: where the git repository is located

    Returns: list[last_commit_before_timestamp, ..., initial_commits]
    """
    return [
        FullCommitHash(hash_val) for hash_val in git(
            __get_git_path_arg(repo_folder), "rev-list",
            f"--before={timestamp}", "HEAD"
        ).split()
    ]


def get_commits_after_timestamp(
    timestamp: str,
    repo_folder: tp.Optional[Path] = None
) -> tp.List[FullCommitHash]:
    """
    Get all commits after a specific timestamp (given as a git date format).

    Note: for imprecise timestamps (e.g., only 2020), the day and month will
    default to today.

    Args:
        repo_folder: where the git repository is located
        timestamp: after which commits should be collected

    Returns: list[newest_commit, ..., last_commit_after_timestamp]
    """
    return [
        FullCommitHash(hash_val) for hash_val in git(
            __get_git_path_arg(repo_folder), "rev-list", f"--after={timestamp}",
            "HEAD"
        ).split()
    ]


def contains_source_code(
    commit: ShortCommitHash,
    repo_folder: tp.Optional[Path] = None,
    churn_config: tp.Optional['ChurnConfig'] = None
) -> bool:
    """
    Check if a commit contains source code of any language specifyed with the
    churn config.

    Args:
        commit: to check
        repo_folder: of the commits repository
        churn_config: to specify the files that should be considered

    Returns: True, if source code of a language, specified in the churn
        config, was found in the commit
    """
    if not churn_config:
        churn_config = ChurnConfig.create_c_style_languages_config()

    return_code = git[__get_git_path_arg(repo_folder), "diff", "--exit-code",
                      "--quiet", f"{commit.hash}~", commit.hash, "--",
                      churn_config.get_extensions_repr('*.')] & RETCODE

    if return_code == 0:
        return False

    if return_code == 1:
        return True

    raise RuntimeError(f"git diff failed with retcode={return_code}")


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


CommitLookupTy = tp.Callable[[CommitRepoPair], pygit2.Commit]


def create_commit_lookup_helper(project_name: str) -> CommitLookupTy:
    """
    Creates a commit lookup function for project repositories.

    Args:
        project_name: name of the given benchbuild project

    Returns:
        a Callable that maps a commit hash and repository name to the
        corresponding commit.
    """

    repos = get_local_project_gits(project_name)

    def get_commit(crp: CommitRepoPair) -> pygit2.Commit:
        """
        Gets the commit from a given ``CommitRepoPair``.

        Args:
            crp: the ``CommitRepoPair`` for the commit to get


        Returns:
            the commit corresponding to the given CommitRepoPair
        """
        commit = repos[crp.repository_name].get(crp.commit_hash.hash)
        if not commit:
            raise LookupError(
                f"Could not find commit {crp} for project {project_name}."
            )

        return commit

    return get_commit


def get_submodule_head(
    project_name: str, submodule_name: str, commit: FullCommitHash
) -> FullCommitHash:
    """
    Retrieve the checked out commit for a submodule of a project.

    Args:
        project_name: name of the project
        submodule_name: name of the submodule
        commit: commit of the project's main repo

    Returns:
        checked out commit of the submodule
    """
    if submodule_name == get_primary_project_source(project_name).local:
        return commit

    main_repo = get_local_project_git_path(project_name)
    submodule_status = git(__get_git_path_arg(main_repo), "ls-tree", commit)
    commit_pattern = re.compile(
        r"[0-9]* commit ([0-9abcdef]*)\t" + submodule_name
    )
    match = commit_pattern.search(submodule_status)
    if match:
        return FullCommitHash(match.group(1))

    raise AssertionError(f"Unknown submodule {submodule_name}")


MappedCommitResultType = tp.TypeVar("MappedCommitResultType")


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
    repo_path: Path,
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
        repo_path: path to the git repository
        churn_config: churn config to customize churn generation
        start_range: begin churn calculation at start commit
        end_range: end churn calculation at end commit
    """

    churn_values: tp.Dict[FullCommitHash, tp.Tuple[int, int, int]] = {}
    if start_range and start_range == get_initial_commit(repo_path):
        start_range = None

    if start_range is None and end_range is None:
        revision_range = None
    elif start_range is None:
        revision_range = f"{end_range.hash}"  # type: ignore
    elif end_range is None:
        revision_range = f"{start_range.hash}~.."
    else:
        revision_range = f"{start_range.hash}~..{end_range.hash}"

    repo_git = git[__get_git_path_arg(repo_path)]
    log_base_params = ["log", "--pretty=%H"]
    diff_base_params = [
        "log", "--pretty=format:'%H'", "--shortstat", "-l0", "--first-parent"
    ]
    if revision_range:
        log_base_params.append(revision_range)
        diff_base_params.append(revision_range)

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    stdout = repo_git(diff_base_params)
    revs = repo_git(log_base_params).strip().split()

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
    repo_path: Path,
    churn_config: tp.Optional[ChurnConfig] = None,
    start_range: tp.Optional[FullCommitHash] = None,
    end_range: tp.Optional[FullCommitHash] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range.

    [start..end]. If no range is supplied, the churn values of all commits are
    calculated.

    Args:
        repo_path: path to git repository
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return __calc_code_churn_range_impl(
        repo_path, churn_config, start_range, end_range
    )


def calc_commit_code_churn(
    repo_path: Path,
    commit_hash: FullCommitHash,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Tuple[int, int, int]:
    """
    Calculates churn of a specific commit.

    Args:
        repo_path: path to git repository
        commit_hash: commit hash to get churn for
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(
        repo_path, churn_config, commit_hash, commit_hash
    )[commit_hash]


def calc_code_churn(
    repo_path: Path,
    commit_a: FullCommitHash,
    commit_b: FullCommitHash,
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
    diff_base_params = [
        "diff", "--shortstat", "-l0", commit_a.hash, commit_b.hash
    ]

    if not churn_config.include_everything:
        diff_base_params.append("--")
        # builds a regex to select files that git includes into churn calc
        diff_base_params = diff_base_params + \
                           churn_config.get_extensions_repr('*.')

    stdout = git(__get_git_path_arg(repo_path), diff_base_params)
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
    repo_path: Path,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Dict[FullCommitHash, tp.Tuple[int, int, int]]:
    """
    Calculates code churn for a repository.

    Args:
        repo: path to git repository
        churn_config: churn config to customize churn generation

    Returns:
        dict of churn triples, where the commit hash points to
        (files changed, insertions, deletions)
    """
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    return calc_code_churn_range(repo_path, churn_config)


def __print_calc_repo_code_churn(
    repo: pygit2.Repository,
    churn_config: tp.Optional[ChurnConfig] = None
) -> None:
    """Prints calc repo code churn data like git log would do."""
    churn_config = ChurnConfig.init_as_default_if_none(churn_config)
    churn_map = calc_repo_code_churn(Path(repo.path), churn_config)

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


def calc_repo_loc(repo: pygit2.Repository, rev_range: str) -> int:
    """
    Calculate the LOC for a project at its HEAD.

    Args:
        repo: the repository to calculate the LOC for

    Returns:
        the number of lines in source-code files
    """
    project_path = repo.path[:-5]
    churn_config = ChurnConfig.create_c_style_languages_config()
    file_pattern = re.compile(
        "|".join(churn_config.get_extensions_repr(r"^.*\.", r"$"))
    )

    loc: int = 0
    with local.cwd(project_path):
        files = git(
            "ls-tree",
            "-r",
            "--name-only",
            rev_range,
        ).splitlines()

        for file in files:
            if file_pattern.match(file):
                lines = git("show", f"{rev_range}:{file}").splitlines()
                loc += len([line for line in lines if line])

    return loc


################################################################################
# Special git-specific classes


class RevisionBinaryMap(tp.Container[str]):
    """A special map that specifies for which revision ranges a binaries is
    valid."""

    def __init__(self, repo_location: Path) -> None:
        self.__repo_location = repo_location
        self.__revision_specific_mappings: tp.Dict[RevisionRange,
                                                   ProjectBinaryWrapper] = {}
        self.__always_valid_mappings: tp.List[ProjectBinaryWrapper] = []

    def specify_binary(
        self, location: str, binary_type: BinaryType, **kwargs: tp.Any
    ) -> None:
        """

        Args:
            location: where the binary can be found, relative to the
                      project-source root
            binary_type: the type of binary that is produced
            override_binary_name: overrides the used binary name
            override_entry_point: overrides the executable entry point
            only_valid_in: additionally specifies a validity range that
                           specifies in which revision range this binary is
                           produced
        """
        binary_location_path = Path(location)
        binary_name: str = kwargs.get(
            "override_binary_name", binary_location_path.stem
        )
        override_entry_point = kwargs.get("override_entry_point", None)
        if override_entry_point:
            override_entry_point = Path(override_entry_point)
        validity_range = kwargs.get("only_valid_in", None)

        wrapped_binary = ProjectBinaryWrapper(
            binary_name, binary_location_path, binary_type, override_entry_point
        )

        if validity_range:
            self.__revision_specific_mappings[validity_range] = wrapped_binary
        else:
            self.__always_valid_mappings.append(wrapped_binary)

    def __getitem__(self,
                    revision: ShortCommitHash) -> tp.List[ProjectBinaryWrapper]:
        revision_specific_binaries = []

        for validity_range, wrapped_binary \
                in self.__revision_specific_mappings.items():
            if revision in get_all_revisions_between(
                validity_range.id_start, validity_range.id_end, ShortCommitHash,
                self.__repo_location
            ):
                revision_specific_binaries.append(wrapped_binary)

        revision_specific_binaries.extend(self.__always_valid_mappings)

        return revision_specific_binaries

    def __contains__(self, binary_name: object) -> bool:
        if isinstance(binary_name, str):
            for binary in chain(
                self.__always_valid_mappings,
                self.__revision_specific_mappings.values()
            ):
                if binary.name == binary_name:
                    return True

        return False


def has_branch(repo_folder: Path, branch_name: str) -> bool:
    """Checks if a branch exists in the local repository."""

    exit_code = git["-C",
                    repo_folder.absolute(), "rev-parse", "--verify",
                    branch_name] & TF
    return tp.cast(bool, exit_code)


def has_remote_branch(repo_folder: Path, branch_name: str, remote: str) -> bool:
    """Checks if a remote branch of a repository exists."""
    exit_code = (
        git["-C",
            repo_folder.absolute(), "ls-remote", "--heads", remote, branch_name]
        | grep[branch_name]
    ) & RETCODE
    return tp.cast(bool, exit_code == 0)


def branch_has_upstream(
    repo_folder: Path, branch_name: str, upstream: str = 'origin'
) -> bool:
    """Check if a branch has an upstream remote."""
    exit_code = (
        git["-C",
            repo_folder.absolute(), "rev-parse", "--abbrev-ref",
            branch_name + "@{upstream}"] | grep[upstream]
    ) & RETCODE
    return tp.cast(bool, exit_code == 0)

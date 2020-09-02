"""Utility module for handling git repos."""

import re
import typing as tp
from enum import Enum

import pygit2
from benchbuild.utils.cmd import git
from plumbum import local

from varats.utils.project_util import get_local_project_git


class ChurnConfig():
    """
    The churn config allows the user to change how code churn is calculated.

    Churn is by default calulcated considering all files in a repository. Users
    can select a specific set of file extensions to only be considered in the
    code churn, e.g., by selecting `h` and `c` only C related files will be used
    to compute the code churn.
    """

    class Language(Enum):

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

    def get_extensions_repr(self, sep: str = ", ") -> str:
        """
        Returns a string that containts all file extensions from all enabled
        languages.

        Args:
            sep: separator inserted between file extensions

        Returns:
            string representation of all enabled extension types
        """
        concat_str = ""
        tmp_sep = ""
        for ext in sorted({
            ext for lang in self.enabled_languages for ext in lang.value
        }):
            concat_str += tmp_sep
            tmp_sep = sep
            concat_str += ext

        return concat_str


def create_commit_lookup_helper(
    project_name: str
) -> tp.Callable[[str], pygit2.Commit]:
    """Creates a commit lookup function for a specific repository."""

    cache_dict: tp.Dict[str, pygit2.Commit] = {}
    repo = get_local_project_git(project_name)

    def get_commit(c_hash: str) -> pygit2.Commit:
        if c_hash in cache_dict:
            return cache_dict[c_hash]

        commit = repo.get(c_hash)
        if commit is None:
            raise LookupError(
                "Could not find commit {commit} in {project}".format(
                    commit=c_hash, project=project_name
                )
            )

        cache_dict[c_hash] = commit
        return commit

    return get_commit


MappedCommitResultType = tp.TypeVar("MappedCommitResultType")


def map_commits(
    func: tp.Callable[[pygit2.Commit], MappedCommitResultType],
    c_hash_list: tp.Iterable[str], commit_lookup: tp.Callable[[str],
                                                              pygit2.Commit]
) -> tp.Sequence[MappedCommitResultType]:
    """Maps a functions over a range of commits."""
    # Skip 0000 hashes that we added to mark uncommitted files
    return [
        func(commit_lookup(c_hash))
        for c_hash in c_hash_list
        if c_hash != "0000000000000000000000000000000000000000"
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
) -> tp.Dict[str, tp.Tuple[int, int, int]]:
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

    churn_values: tp.Dict[str, tp.Tuple[int, int, int]] = {}

    if start_range is None and end_range is None:
        revision_range = None
    elif start_range is None:
        revision_range = "..{}".format(end_range)
    elif end_range is None:
        revision_range = "{}~..".format(start_range)
    else:
        revision_range = "{}~..{}".format(start_range, end_range)

    with local.cwd(repo_path):
        log_base_params = ["log", "--pretty=%H"]
        diff_base_params = [
            "log", "--pretty=format:'%H'", "--date=short", "--shortstat", "-l0"
        ]
        if revision_range:
            log_base_params.append(revision_range)
            diff_base_params.append(revision_range)

        if not churn_config.include_everything:
            diff_base_params.append("--")
            # builds a regrex to select files that git includes into churn calc
            diff_base_params.append(
                ":*.[" + churn_config.get_extensions_repr('|') + "]"
            )

        if revision_range:
            stdout = git(diff_base_params)
            revs = git(log_base_params).strip().split()
        else:
            stdout = git(diff_base_params)
            revs = git(log_base_params).strip().split()
        # initialize with 0 as otherwise commits without changes would be
        # missing from the churn data
        for rev in revs:
            churn_values[rev] = (0, 0, 0)
        for match in GIT_LOG_MATCHER.finditer(stdout):
            commit_hash = match.group('hash')
            files_changed_m = match.group('files')
            files_changed = int(
                files_changed_m
            ) if files_changed_m is not None else 0
            insertions_m = match.group('insertions')
            insertions = int(insertions_m) if insertions_m is not None else 0
            deletions_m = match.group('deletions')
            deletions = int(deletions_m) if deletions_m is not None else 0
            churn_values[commit_hash] = (files_changed, insertions, deletions)

    return churn_values


def calc_code_churn_range(
    repo: tp.Union[pygit2.Repository, str],
    churn_config: tp.Optional[ChurnConfig] = None,
    start_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None,
    end_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None
) -> tp.Dict[str, tp.Tuple[int, int, int]]:
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
    return calc_code_churn_range(repo, churn_config, commit,
                                 commit)[str(commit.id)]


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
    with local.cwd(repo.path):
        diff_base_params = [
            "diff", "--shortstat", "-l0",
            str(commit_a.id),
            str(commit_b.id)
        ]

        if not churn_config.include_everything:
            diff_base_params.append("--")
            # builds a regrex to select files that git includes into churn calc
            diff_base_params.append(
                ":*.[" + churn_config.get_extensions_repr('|') + "]"
            )

        stdout = git(diff_base_params)
        # initialize with 0 as otherwise commits without changes would be
        # missing from the churn data
        match = GIT_DIFF_MATCHER.match(stdout)
        if match:
            files_changed_m = match.group('files')
            files_changed = int(
                files_changed_m
            ) if files_changed_m is not None else 0
            insertions_m = match.group('insertions')
            insertions = int(insertions_m) if insertions_m is not None else 0
            deletions_m = match.group('deletions')
            deletions = int(deletions_m) if deletions_m is not None else 0
            return files_changed, insertions, deletions

    return 0, 0, 0


def calc_repo_code_churn(
    repo: pygit2.Repository,
    churn_config: tp.Optional[ChurnConfig] = None
) -> tp.Dict[str, tp.Tuple[int, int, int]]:
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
        commit_hash = str(commit.id)
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

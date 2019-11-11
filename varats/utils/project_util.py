"""
Utility module for BenchBuild project handling.
"""
import abc
from pathlib import Path
import typing as tp
import tempfile

from plumbum import local

from benchbuild.project import ProjectRegistry, Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import git
from benchbuild.utils.download import Git
from benchbuild.utils.settings import setup_config

from varats.settings import CFG


def get_project_cls_by_name(project_name: str) -> Project:
    """
    Look up a BenchBuild project by it's name.
    """
    for proj in ProjectRegistry.projects:
        if proj.endswith('gentoo') or proj.endswith("benchbuild"):
            # currently we only support vara provided projects
            continue

        if proj.startswith(project_name):
            return ProjectRegistry.projects[proj]

    raise LookupError


def get_local_project_git_path(project_name: str) -> Path:
    """
    Get the path to the local download location of git repository
    for a given benchbuild project.
    """
    setup_config(BB_CFG, [str(CFG['benchbuild_root']) + "/.benchbuild.yml"])

    project_git_path = Path(str(CFG['benchbuild_root'])) / str(
        BB_CFG["tmp_dir"])
    project_git_path /= project_name if project_name.endswith(
        "-HEAD") else project_name + "-HEAD"

    if not project_git_path.exists():
        project_cls = get_project_cls_by_name(project_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            with local.cwd(tmpdir):
                Git(project_cls.repository,
                    project_cls.SRC_FILE,
                    shallow_clone=False)

    return project_git_path


def get_tagged_commits(project_name: str) -> tp.List[tp.Tuple[str, str]]:
    """
    Get a list of all tagged commits along with their respective tags.
    """
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


def get_all_revisions_between(a: str, b: str) -> tp.List[str]:
    """
    Returns a list of all revisions between two commits a and b (inclusive),
    where a comes before b.
    It is assumed that the current working directory is the git repository.
    """
    result = [a]
    result.extend(
        git("log", "--pretty=%H", "--ancestry-path",
            "{}..{}".format(a, b)).strip().split())
    return result


class BlockedRevision():
    """
    A revision marked as blocked due to some `reason`.
    """

    def __init__(self, rev_id: str, reason: tp.Optional[str] = None):
        self.__id = rev_id
        self.__reason = reason

    @property
    def reason(self):
        """
        The reason why this revision is blocked.
        """
        return self.__reason

    def __iter__(self):
        return [self.__id].__iter__()


class BlockedRevisionRange():
    """
    A range of revisions marked as blocked due to some `reason`.
    """

    def __init__(self,
                 id_start: str,
                 id_end: str,
                 reason: tp.Optional[str] = None):
        self.__id_start = id_start
        self.__id_end = id_end
        self.__reason = reason
        # cache for commit hashes
        self.__revision_list: tp.Optional[tp.List[str]] = None

    @property
    def reason(self):
        """
        The reason why this revision range is blocked.
        """
        return self.__reason

    def __iter__(self):
        if self.__revision_list is None:
            self.__revision_list = get_all_revisions_between(
                self.__id_start, self.__id_end)

        return self.__revision_list.__iter__()


def block_revisions(
        blocks: tp.List[tp.Union[BlockedRevision, BlockedRevisionRange]]):
    """
    Decorator for project classes for blacklisting/blocking revisions.

    This adds a new static method `is_blocked_revision` that checks
    whether a given revision id is marked as blocked.

    Args:
        blocks: A list of `BlockedRevision`s and `BlockedRevisionRange`s.
    """

    def revision_blocker_decorator(cls):
        cls.__project_path = get_local_project_git_path(cls.NAME)
        cls.__blacklist_entries = blocks

        @staticmethod
        def is_blocked_revision_impl(
                rev_id: str) -> tp.Tuple[bool, tp.Optional[str]]:
            """
            Checks whether a revision is blocked or not. Also returns the
            reason for the block if available.
            """
            # cd to repo because of potential git lookups
            with local.cwd(cls.__project_path):
                for b_entry in cls.__blacklist_entries:
                    for b_item in b_entry:
                        if b_item.startswith(rev_id):
                            return True, b_entry.reason
            return False, None

        cls.is_blocked_revision = is_blocked_revision_impl
        return cls

    return revision_blocker_decorator

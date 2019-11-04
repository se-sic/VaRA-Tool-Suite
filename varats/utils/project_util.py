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


def get_all_revisions_between(a: str, b: str) -> tp.List[str]:
    """
    Returns a list of all revisions between two commits a and b, 
    where a comes before b.
    It is assumed that the current working directory is the git repository. 
    """
    return git("log", "--pretty=%H", "--ancestry-path",
               "{}^..{}".format(a, b)).strip().split()


class BlockedRevision():
    """
    A revision marked as blocked due to some `reason`.
    """

    def __init__(self, id: str, reason: tp.Optional[str] = None):
        self.__id = id
        self.__reason = reason

    @property
    def reason(self):
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
        return self.__reason

    def __iter__(self):
        if self.__revision_list is None:
            self.__revision_list = get_all_revisions_between(
                self.__id_start, self.__id_end)

        return self.__revision_list.__iter__()


class BlockedRevisionChecker():
    """
    Interface for blacklisting/blocking revisions from a project.
    Implementors should delegate to an instance of
    `BlockedRevisionCheckerDelegate`.
    """

    @classmethod
    @abc.abstractmethod
    def is_blocked_revision(cls, id: str) -> tp.Tuple[bool, tp.Optional[str]]:
        """
        Checks whether a revision is blocked or not. Also returns the 
        reason for the block if available.
        """


class BlockedRevisionCheckerDelegate():
    """
    Delegate for the
    """

    def __init__(self, project_name: str) -> None:
        self.__project_name = project_name
        self.__project_path = get_local_project_git_path(project_name)

        self.__blacklist_entries: tp.List[
            tp.Union[BlockedRevision, BlockedRevisionRange]] = []

    def is_blocked_revision(self, id: str) -> tp.Tuple[bool, tp.Optional[str]]:
        # cd to repo because of potential git lookups
        with local.cwd(self.__project_path):
            for b_entry in self.__blacklist_entries:
                for b_item in b_entry:
                    if id == b_item:
                        return False, b_entry.reason
        return True, None

    def block_revision(self, id: str, reason: tp.Optional[str] = None) -> None:
        """
        Blacklist a single revision.
        """
        self.__blacklist_entries.append(BlockedRevision(id, reason))

    def block_revisions(self,
                        id_start: str,
                        id_end: str,
                        reason: tp.Optional[str] = None) -> None:
        """
        Blacklist all revisions between commit `id_start` (older)
        and `id_end` (newer).
        """
        self.__blacklist_entries.append(
            BlockedRevisionRange(id_start, id_end, reason))

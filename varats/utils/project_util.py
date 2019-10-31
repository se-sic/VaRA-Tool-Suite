"""
Utility module for BenchBuild project handling.
"""

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

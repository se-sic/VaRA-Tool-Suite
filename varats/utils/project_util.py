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


def wrap_paths_to_binaries(binaries: tp.List[str]) -> tp.List[Path]:
    """
    Generates a wrapper for project binaries.

    >>> wrap_paths_to_binaries(["src/foo"])
    [PosixPath('src/foo')]

    >>> wrap_paths_to_binaries(["src/foo", "src/bar"])
    [PosixPath('src/foo'), PosixPath('src/bar')]
    """
    return [Path(x) for x in binaries]

"""
Commit map module.
"""

from pathlib import Path

from plumbum import local
from plumbum.cmd import git, mkdir

from varats.data.commit_report import CommitMap
from varats.utils.project_util import get_local_project_git_path


def generate_commit_map(path: Path, end="HEAD", start=None):
    """
    Generate a commit map for a repository including the commits ]start..end]
    """
    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        full_out = git("--no-pager", "log", "--pretty=format:'%H'")
        wanted_out = git("--no-pager", "log", "--pretty=format:'%H'",
                         search_range)

        def format_stream():
            wanted_cm = set()
            for line in wanted_out.split('\n'):
                wanted_cm.add(line[1:-1])

            for number, line in enumerate(reversed(full_out.split('\n'))):
                line = line[1:-1]
                if line in wanted_cm:
                    yield "{}, {}\n".format(number, line)

        return CommitMap(format_stream())


def store_commit_map(cmap: CommitMap, output_file_path: str):
    """
    Store commit map to file.
    """
    mkdir("-p", Path(output_file_path).parent)

    with open(output_file_path, "w") as c_map_file:
        cmap.write_to_file(c_map_file)


def load_commit_map_from_path(cmap_path: Path) -> CommitMap:
    """
    Load a commit map from a given `.cmap` file path.
    """
    with open(cmap_path, "r") as c_map_file:
        return CommitMap(c_map_file.readlines())


def get_commit_map(project_name: str,
                   cmap_path: Path = None,
                   end="HEAD",
                   start=None) -> CommitMap:
    """
    Get a commit map for a project.
    """
    if cmap_path is None:
        project_git_path = get_local_project_git_path(project_name)

        return generate_commit_map(project_git_path, end, start)

    return load_commit_map_from_path(cmap_path)


def create_lazy_commit_map_loader(project,
                                  cmap_path: Path,
                                  end="HEAD",
                                  start=None):
    """
    Create a generator function that lazy loads a CommitMap.
    """
    lazy_cached_cmap = None

    def get_cmap_lazy():
        nonlocal lazy_cached_cmap
        if lazy_cached_cmap is None:
            lazy_cached_cmap = get_commit_map(project, cmap_path, end, start)

        return lazy_cached_cmap

    return get_cmap_lazy

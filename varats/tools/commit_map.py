"""
Commit map module.
"""

from pathlib import Path

from plumbum import local
from plumbum.cmd import git, mkdir

from varats.data.commit_report import CommitMap


def generate_commit_map(path: str, end="HEAD", start=None):
    """
    Generate a commit map for a repository including the commits ]start..end]
    """
    print("Generating commit map for:", path)

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

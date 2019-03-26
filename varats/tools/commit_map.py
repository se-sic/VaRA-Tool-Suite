"""
Commit map module.
"""

from pathlib import Path

from plumbum import local
from plumbum.cmd import git, mkdir


def generate_commit_map(path: str, output_filename: str, end="HEAD",
                        start=None):
    """
    Generate a commit map for a repository including the commits ]start..end]
    """
    print("Generating commit map for:", path)

    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        out = git("--no-pager", "log", "--pretty=format:'%H'",
                  search_range)

    mkdir("-p", Path(output_filename).parent)

    with open(output_filename, "w") as c_map:
        for number, line in enumerate(reversed(out.split('\n'))):
            line = line[1:-1]
            c_map.write("{}, {}\n".format(number, line))

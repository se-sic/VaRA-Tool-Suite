"""The development module provides different utility function to ease the
development for VaRA."""

import logging
import re
import typing as tp
from collections import defaultdict

from varats.tools.research_tools.research_tool import CodeBase, SubProject
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def __convert_to_vara_branch_naming_schema(branch_name: str) -> str:
    """
    Converts a branch_name to the VaRA branch naming schema. Every feature
    branch needs to start with `f-` so certain tools, like the buildbot,
    automatically recognize them.

    Test:
    >>> __convert_to_vara_branch_naming_schema("Foo")
    'f-Foo'

    >>> __convert_to_vara_branch_naming_schema("f-Foo")
    'f-Foo'
    """
    return branch_name if branch_name.startswith("f-") else "f-" + branch_name


def __quickfix_dev_branches(branch_name: str, sub_project: SubProject) -> str:
    """
    Fix vara branches names for checking out master or dev branches.

    Test:
    >>> import re
    >>> fixed_branch_name = __quickfix_dev_branches(\
        'vara-dev', SubProject(None, "vara-llvm-project", "", "", ""))
    >>> re.match(r'vara-\\d+-dev', fixed_branch_name) is not None
    True

    >>> fixed_branch_name = __quickfix_dev_branches(\
        'vara', SubProject(None, "vara-llvm-project", "", "", ""))
    >>> re.match(r'vara-\\d+', fixed_branch_name) is not None
    True

    >>> __quickfix_dev_branches(\
        "f-FooBar", SubProject(None, "vara-llvm-project", "", "", ""))
    'f-FooBar'

    >>> __quickfix_dev_branches(\
        "vara-dev", SubProject(None, "vara", "", "", ""))
    'vara-dev'
    """
    if sub_project.name == "vara-llvm-project":
        version = str(vara_cfg()['vara']['version'])
        if branch_name == 'vara-dev':
            return f"vara-{version}-dev"
        if branch_name == 'vara':
            return f"vara-{version}"

    return branch_name


def create_new_branch_for_projects(
    branch_name: str, sub_projects: tp.List[SubProject]
) -> None:
    """Create a new branch on all needed projects."""
    branch_name = __convert_to_vara_branch_naming_schema(branch_name)

    for sub_project in sub_projects:
        if not sub_project.has_branch(branch_name):
            sub_project.checkout_new_branch(branch_name)
            print(f"Created new branch {branch_name}")
        else:
            print(f"Branch {branch_name} does already exist.")


def checkout_remote_branch_for_projects(
    branch_name: str, sub_projects: tp.List[SubProject]
) -> None:
    """Checkout a remote branch on all projects."""
    for sub_project in sub_projects:
        fixed_branch_name = __quickfix_dev_branches(branch_name, sub_project)
        if sub_project.has_branch(fixed_branch_name):
            sub_project.checkout_branch(fixed_branch_name)
            print(
                f"Checked out existing branch {fixed_branch_name} "
                f"for sub project {sub_project.name}"
            )
            continue

        sub_project.fetch()
        if sub_project.has_branch(fixed_branch_name, "origin"):
            sub_project.checkout_new_branch(
                fixed_branch_name, f"origin/{fixed_branch_name}"
            )
            print(
                f"Checked out new branch {fixed_branch_name} "
                f"(tracking origin/{fixed_branch_name}) "
                f"for sub project {sub_project.name}"
            )
        else:
            print(
                f"No branch {fixed_branch_name} on remote origin for project "
                f"{sub_project.name}"
            )


def pull_projects(sub_projects: tp.List[SubProject]) -> None:
    """
    Pull the current branch of all sub_projects in a code_base.

    Args:
        sub_projects: a list of sub_projects from the code base
                      that should be handled
    """

    for sub_project in sub_projects:
        print(f"Pulling {sub_project.name}")
        sub_project.pull()


def push_projects(sub_projects: tp.List[SubProject]) -> None:
    """
    Push the current branch of all projects.

    Args:
        sub_projects: a list of sub_projects from the code base
                      that should be handled
    """
    for sub_project in sub_projects:
        print(f"Pushing {sub_project.name}")
        sub_project.push()


def show_status_for_projects(sub_projects: tp.List[SubProject]) -> None:
    """
    Show the status of all sub projects of a code base.

    Args:
        sub_projects: a list of sub_projects from the code base
                      that should be handled
    """

    dlim = "#" * 80
    for sub_project in sub_projects:
        print(
            """
{dlim}
# Project: {name:67s} #
{dlim}""".format(dlim=dlim, name=sub_project.name)
        )

        sub_project.show_status()


def show_dev_branches(code_base: CodeBase) -> None:
    """Show all dev dev branches."""
    found_branches: tp.DefaultDict[str, tp.List[str]] = defaultdict(list)
    max_branch_chars = 0

    def __handle_sub_project(sub_project: SubProject) -> None:
        """"""
        nonlocal max_branch_chars
        sub_project.fetch("origin", extra_args=["--prune"])
        for full_branch in sub_project.get_branches(extra_args=["-r"]):
            match = re.match(r".*(f-.*)", full_branch)
            if match is not None:
                branch_name = match.group(1).strip()
                if len(branch_name) > max_branch_chars:
                    max_branch_chars = len(branch_name)
                found_branches[branch_name] += [sub_project.name]

    code_base.map_sub_projects(__handle_sub_project)

    print("Feature Branches:")
    for branch_name, repos in found_branches.items():
        print(("  {branch_name:" + str(max_branch_chars + 4) +
               "s} {repos}").format(branch_name=branch_name, repos=repos))

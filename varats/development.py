"""
The development module provides different utility function to ease the
development for VaRA.
"""

import typing as tp
from collections import defaultdict
from pathlib import Path
import re

from varats.settings import CFG
from varats.vara_manager import (
    checkout_branch, checkout_new_branch, get_current_branch, has_branch,
    has_remote_branch, branch_has_upstream, fetch_repository, fetch_remote,
    show_status, get_branches, pull_current_branch, push_current_branch,
    LLVMProjects, LLVMProject)


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


def __quickfix_dev_branches(branch_name: str, project: LLVMProject) -> str:
    """
    Fix vara branches names for checking out master or dev branches.

    Test:
    >>> import re
    >>> fixed_branch_name = __quickfix_dev_branches(\
        'vara-dev', LLVMProjects.llvm.project)
    >>> re.match(r'vara-\\d+-dev', fixed_branch_name) is not None
    True

    >>> fixed_branch_name = __quickfix_dev_branches(\
        'vara', LLVMProjects.clang.project)
    >>> re.match(r'vara-\\d+', fixed_branch_name) is not None
    True

    >>> __quickfix_dev_branches(\
        "f-FooBar", LLVMProjects.clang.project)
    'f-FooBar'

    >>> __quickfix_dev_branches(\
        "vara-dev", LLVMProjects.vara.project)
    'vara-dev'
    """
    if project is LLVMProjects.get_project_by_name(
            'llvm') or project is LLVMProjects.get_project_by_name('clang'):
        if branch_name == 'vara-dev':
            return 'vara-{version}-dev'.format(version=str(CFG['version']))
        if branch_name == 'vara':
            return 'vara-{version}'.format(version=str(CFG['version']))

    return branch_name


def create_new_branch_for_projects(branch_name: str,
                                   projects: tp.List[LLVMProjects]) -> None:
    """
    Create a new branch on all needed projects.
    """
    branch_name = __convert_to_vara_branch_naming_schema(branch_name)
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    for project in projects:
        if project.is_extra_project():
            import warnings
            warnings.warn("vara-develop can only create branches for VaRA " +
                          "related projects not extra LLVMProjects.")
            continue

        if not has_branch(llvm_folder / project.path, branch_name):
            checkout_new_branch(llvm_folder / project.path, branch_name)


def checkout_branch_for_projects(branch_name: str,
                                 projects: tp.List[LLVMProjects]) -> None:
    """
    Checkout a branch on all projects.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    for project in projects:
        fixed_branch_name = __quickfix_dev_branches(branch_name,
                                                    project.project)
        if has_branch(llvm_folder / project.path, fixed_branch_name):
            checkout_branch(llvm_folder / project.path, fixed_branch_name)
            print(
                "Checked out new branch {branch} for project {project}".format(
                    branch=fixed_branch_name, project=project.name))
        else:
            print("No branch {branch} for project {project}".format(
                branch=fixed_branch_name, project=project.name))


def checkout_remote_branch_for_projects(
        branch_name: str, projects: tp.List[LLVMProjects]) -> None:
    """
    Checkout a remote branch on all projects.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    for project in projects:
        fixed_branch_name = __quickfix_dev_branches(branch_name,
                                                    project.project)
        if has_branch(llvm_folder / project.path, fixed_branch_name):
            print(
                "Checked out new branch {branch} for project {project}".format(
                    branch=fixed_branch_name, project=project.name))
            continue

        fetch_repository(llvm_folder / project.path)
        if has_remote_branch(llvm_folder / project.path, fixed_branch_name,
                             'origin'):
            checkout_new_branch(llvm_folder / project.path, fixed_branch_name)
            print(
                "Checked out new branch {branch} for project {project}".format(
                    branch=fixed_branch_name, project=project.name))
        else:
            print("No branch {branch} on remote origin for project {project}".
                  format(branch=fixed_branch_name, project=project.name))


def pull_projects(projects: tp.List[LLVMProjects]) -> None:
    """
    Pull the current branch of all projects.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    for project in projects:
        print("Pulling {project}".format(project=project.project_name))
        pull_current_branch(llvm_folder / project.path)


def push_projects(projects: tp.List[LLVMProjects]) -> None:
    """
    Push the current branch of all projects.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    for project in projects:
        print("Pushing {project}".format(project=project.project_name))

        branch_name = get_current_branch(llvm_folder / project.path)
        if branch_has_upstream(llvm_folder / project.path, branch_name):
            push_current_branch(llvm_folder / project.path)
        else:
            push_current_branch(llvm_folder / project.path, 'origin',
                                branch_name)


def show_status_for_projects(projects: tp.List[LLVMProjects]) -> None:
    """
    Show the status of all projects.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    dlim = "#" * 80
    for project in projects:
        print("""
{dlim}
# Project: {name:67s} #
{dlim}""".format(dlim=dlim, name=project.project_name))
        show_status(llvm_folder / project.path)


def show_dev_branches(
        projects: tp.List[tp.Union[LLVMProject, LLVMProjects]]) -> None:
    """
    Show all dev dev branches.
    """
    llvm_folder = Path(str(CFG['llvm_source_dir']))

    found_branches: tp.DefaultDict[str, tp.List[str]] = defaultdict(list)
    max_branch_chars = 0
    for project in projects:
        if isinstance(project, LLVMProjects):
            project = project.project

        fetch_remote(
            "origin", llvm_folder / project.path, extra_args=["--prune"])
        branches = get_branches(llvm_folder / project.path, extra_args=["-r"])
        for line in branches.split():
            match = re.match(r".*(f-.*)", line)
            if match is not None:
                branch_name = match.group(1).strip()
                if len(branch_name) > max_branch_chars:
                    max_branch_chars = len(branch_name)
                found_branches[branch_name] += [project.name]

    print("Feature Branches:")
    for branch_name in found_branches.keys():
        print(("  {branch_name:" + str(max_branch_chars + 4) +
               "s} {repos}").format(
                   branch_name=branch_name, repos=found_branches[branch_name]))

"""Driver module for `vara-develop` and its alias `vd`."""

import argparse
import typing as tp

from varats.tools.research_tools import development as dev
from varats.tools.research_tools.research_tool import SubProject
from varats.utils.cli_util import (
    get_research_tool,
    get_supported_research_tool_names,
    initialize_cli_tool,
)


def __sub_project_choices() -> tp.List[str]:
    return ["all", "sub_project_name"]


def main() -> None:
    """Handle and simplify common developer interactions with the project."""
    initialize_cli_tool()
    parser = argparse.ArgumentParser("vara-develop")
    parser.add_argument(
        "researchtool",
        help="The research tool one wants to setup",
        choices=get_supported_research_tool_names()
    )
    sub_parsers = parser.add_subparsers(help="Sub commands", dest="command")

    # new-branch
    new_branch_parser = sub_parsers.add_parser('new-branch')
    new_branch_parser.add_argument(
        'branch_name', type=str, help='Name of the new branch'
    )
    new_branch_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        help="Projects to work on."
    )

    # checkout
    checkout_parser = sub_parsers.add_parser('checkout')
    checkout_parser.add_argument(
        'branch_name', type=str, help='Name of the new branch'
    )
    checkout_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        help="Projects to work on."
    )

    # git pull
    pull_parser = sub_parsers.add_parser('pull')
    pull_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        help="Projects to work on."
    )

    # git push
    push_parser = sub_parsers.add_parser('push')
    push_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        help="Projects to work on."
    )

    # git status
    status_parser = sub_parsers.add_parser('status')
    status_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        help="Projects to work on. Or all/all-vara for all projects."
    )

    # list dev-branches
    sub_parsers.add_parser(
        'f-branches', help="List all remote feature branches"
    )

    args = parser.parse_args()

    tool = get_research_tool(args.researchtool)

    project_list: tp.List[SubProject] = []

    if hasattr(args, "projects"):
        project_list = []
        if "all" in args.projects:
            tool.code_base.map_sub_projects(project_list.append)
        else:

            def __project_selector(sub_project: SubProject) -> None:
                lower_name = sub_project.name.lower()
                requested_sub_projects = args.projects
                map(str.lower, requested_sub_projects)
                if lower_name in requested_sub_projects:
                    project_list.append(sub_project)

            tool.code_base.map_sub_projects(__project_selector)

    if args.command == 'new-branch':
        dev.create_new_branch_for_projects(args.branch_name, project_list)
    elif args.command == 'checkout':
        dev.checkout_remote_branch_for_projects(args.branch_name, project_list)
    elif args.command == 'pull':
        dev.pull_projects(project_list)
    elif args.command == 'push':
        dev.push_projects(project_list)
    elif args.command == 'status':
        dev.show_status_for_projects(project_list)
    elif args.command == 'f-branches':
        dev.show_dev_branches(tool.code_base)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

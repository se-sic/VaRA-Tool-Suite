"""
Driver module for `vara-develop` and its alias `vd`.
"""


import argparse
import typing as tp

from varats import development as dev
from varats.vara_manager import (generate_full_list_of_llvmprojects,
                                 LLVMProjects,
                                 generate_vara_list_of_llvmprojects,
                                 convert_to_llvmprojects_enum)


def main() -> None:
    """
    Handle and simplify common developer interactions with the project.
    """
    parser = argparse.ArgumentParser("Developer helper")
    sub_parsers = parser.add_subparsers(help="Sub commands", dest="command")

    # new-branch
    new_branch_parser = sub_parsers.add_parser('new-branch')
    new_branch_parser.add_argument('branch_name',
                                   type=str,
                                   help='Name of the new branch')
    new_branch_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        choices=[
            'all', 'all-vara', 'vara',
            *[x.project_name for x in generate_full_list_of_llvmprojects()]
        ],
        default=None,
        help="Projects to work on.")

    # checkout
    checkout_parser = sub_parsers.add_parser('checkout')
    checkout_parser.add_argument('branch_name',
                                 type=str,
                                 help='Name of the new branch')
    checkout_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        default=None,
        choices=[
            'all', 'all-vara', 'vara',
            *[x.project_name for x in generate_full_list_of_llvmprojects()]
        ],
        help="Projects to work on.")

    # git pull
    pull_parser = sub_parsers.add_parser('pull')
    pull_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        choices=[
            'all', 'all-vara', 'vara',
            *[x.project_name for x in generate_full_list_of_llvmprojects()]
        ],
        default=None,
        help="Projects to work on.")

    # git push
    push_parser = sub_parsers.add_parser('push')
    push_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        choices=[
            'all', 'all-vara', 'vara',
            *[x.project_name for x in generate_full_list_of_llvmprojects()]
        ],
        default=None,
        help="Projects to work on.")

    # git status
    status_parser = sub_parsers.add_parser('status')
    status_parser.add_argument(
        'projects',
        nargs='*',
        action='store',
        choices=[
            'all', 'all-vara', 'vara',
            *[x.project_name for x in generate_full_list_of_llvmprojects()]
        ],
        default=None,
        help="Projects to work on. Or all/all-vara for all projects.")

    # list dev-branches
    sub_parsers.add_parser('f-branches',
                           help="List all remote feature branches")

    args = parser.parse_args()
    project_list: tp.List[LLVMProjects] = []
    if hasattr(args, "projects"):
        if "all" in args.projects:
            project_list = generate_full_list_of_llvmprojects()
        elif "all-vara" in args.projects:
            project_list = generate_vara_list_of_llvmprojects()
        else:
            project_list = convert_to_llvmprojects_enum(args.projects)

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
        dev.show_dev_branches([
            LLVMProjects.get_project_by_name("llvm"),
            LLVMProjects.get_project_by_name("clang"),
            LLVMProjects.get_project_by_name("vara")
        ])
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

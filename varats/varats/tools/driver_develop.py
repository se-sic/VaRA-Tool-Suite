"""Driver module for `vara-develop` and its alias `vd`."""

import typing as tp

import click

from varats.tools.research_tools import development as dev
from varats.tools.research_tools.research_tool import SubProject
from varats.tools.tool_util import (
    get_research_tool,
    get_supported_research_tool_names,
)
from varats.ts_utils.cli_util import initialize_cli_tool


@click.group(context_settings={"help_option_names": ['-h', '--help']})
@click.option(
    "-p",
    "--project",
    "projects",
    metavar="PROJECT",
    type=str,
    multiple=True,
    help="Subprojects to work on or 'all' for all subprojects."
)
@click.argument(
    "research_tool", type=click.Choice(get_supported_research_tool_names())
)
@click.pass_context
def main(
    context: click.Context, research_tool: str, projects: tp.List[str]
) -> None:
    """Handle and simplify common developer interactions with the project."""
    initialize_cli_tool()

    tool = get_research_tool(research_tool)
    context.ensure_object(dict)
    context.obj["research_tool"] = tool

    project_list: tp.List[SubProject] = []
    if projects:
        if "all" in projects:
            tool.code_base.map_sub_projects(project_list.append)
        else:

            def __project_selector(sub_project: SubProject) -> None:
                lower_name = sub_project.name.lower()
                requested_sub_projects = projects
                map(str.lower, requested_sub_projects)
                if lower_name in requested_sub_projects:
                    project_list.append(sub_project)

            tool.code_base.map_sub_projects(__project_selector)

    context.obj["project_list"] = project_list


@main.command(help="Create a new branch.")
@click.argument("branch_name", type=str)
@click.pass_context
def new_branch(context: click.Context, branch_name: str) -> None:
    """Create a new feature branch for a research tool."""
    dev.create_new_branch_for_projects(branch_name, context.obj["project_list"])


@main.command(help="Checkout a branch.")
@click.argument("branch_name", type=str)
@click.pass_context
def checkout(context: click.Context, branch_name: str) -> None:
    """Checkout a branch for a research tool."""
    dev.checkout_remote_branch_for_projects(
        branch_name, context.obj["project_list"]
    )


@main.command(help="Git pull the research tool's repository.")
@click.pass_context
def pull(context: click.Context) -> None:
    """Git pull the research tool's repository."""
    dev.pull_projects(context.obj["project_list"])


@main.command(help="Git push the research tool's repository.")
@click.pass_context
def push(context: click.Context) -> None:
    """Git push the research tool's repository."""
    dev.push_projects(context.obj["project_list"])


@main.command(help="Show git status for a research tool.")
@click.pass_context
def status(context: click.Context) -> None:
    """Show git status for a research tool."""
    dev.show_status_for_projects(context.obj["project_list"])


@main.command(help="List all remote feature branches.")
@click.pass_context
def f_branches(context: click.Context) -> None:
    """List all remote feature branches."""
    dev.show_dev_branches(context.obj["research_tool"].code_base)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter

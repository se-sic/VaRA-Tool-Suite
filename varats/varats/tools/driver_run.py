"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import itertools
import logging
import typing as tp

import click

from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.utils.cli_util import initialize_cli_tool, make_cli_option
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg

LOG = logging.Logger(__name__)


def _validate_project_parameters(
    ctx: tp.Optional[click.Context], param: tp.Optional[click.Parameter],
    value: tp.Tuple[str, ...]
) -> tp.Tuple[str, ...]:
    """
    Sanity-check project/version specification.

    Currently, we only support the ``<project>@<revision>`` syntax. Checks
    whether ``project`` and (if available) ``version`` is selected by one of the
    case studies in the current paper config.
    """
    for project_specifier in value:
        split_input = project_specifier.rsplit('@', maxsplit=1)
        project = split_input[0]
        version = split_input[1] if len(split_input) > 1 else None

        projects: tp.Set[str] = set()
        case_studies: tp.List[CaseStudy] = []
        try:
            paper_config = get_paper_config()
            case_studies = paper_config.get_all_case_studies()
            projects = {cs.project_name for cs in case_studies}
        except ConfigurationLookupError:
            pass

        if project not in projects:
            raise click.BadParameter(
                f"Project '{project}' is not in the current paper config."
            )

        if version:
            commit_hash = ShortCommitHash(version)
            if not any(cs.has_revision(commit_hash) for cs in case_studies):
                raise click.BadParameter(
                    f"Version '{version}' is not selected by any case study."
                )

    return value


@click.command(
    help="Run benchbuild experiments.",
    context_settings={"help_option_names": ['-h', '--help']}
)
@click.option("--slurm", is_flag=True, help="Run experiments on slurm.")
@click.option(
    "--container", is_flag=True, help="Run experiments in a container."
)
@click.option(
    "-E", "--experiment", required=True, help="The experiment to run."
)
@make_cli_option(
    "-p",
    "--project",
    "projects",
    multiple=True,
    callback=_validate_project_parameters,
    help="Only run experiments for the given project."
    "Can be passed multiple times."
)
def main(
    slurm: bool,
    container: bool,
    experiment: str,
    projects: tp.List[str],
) -> None:
    """Manage base container images."""
    initialize_cli_tool()
    initialize_projects()

    bb_command_args: tp.List[str] = []
    bb_extra_args = tp.List[str] = []

    if slurm:
        bb_command_args.append("slurm")

    if container:
        if slurm:
            # TODO: detect whether user should run prepare-slurm
            bb_extra_args = ["--", "container", "run"]
            if bb_cfg()["container"]["import"].value:
                bb_extra_args.append("--import")
        else:
            bb_command_args.append("container")

    if not slurm:
        bb_command_args.append("run")

    if not projects:
        projects = list({
            cs.project_name for cs in get_paper_config().get_all_case_studies()
        })

    bb_args = itertools.chain(
        bb_command_args, ["-E", experiment], projects, bb_extra_args
    )

    print(bb_args)
    # TODO: run BB command

    if slurm:
        # TODO: run sbatch
        pass


if __name__ == '__main__':
    main()

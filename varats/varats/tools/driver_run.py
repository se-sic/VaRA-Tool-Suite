"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import itertools
import logging
import re
import sys
import typing as tp
from pathlib import Path
from subprocess import PIPE

import click
from benchbuild.utils.cmd import benchbuild, sbatch
from plumbum import local
from plumbum.commands import ProcessExecutionError

from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_paper_config
from varats.projects.discover_projects import initialize_projects
from varats.ts_utils.cli_util import initialize_cli_tool, tee
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg, vara_cfg

LOG = logging.Logger(__name__)

__SLURM_SCRIPT_PATTERN = re.compile(r"SLURM script written to (.*\.sh)")


def __validate_project_parameters(
    ctx: tp.Optional[click.Context], param: tp.Optional[click.Parameter],
    value: tp.Tuple[str, ...]
) -> tp.Tuple[str, ...]:
    """
    Sanity-check project/version specification.

    Currently, we only support the ``<project>@<revision>`` syntax. Checks
    whether ``project`` and (if available) ``version`` is selected by one of the
    case studies in the current paper config.
    """
    # pylint: disable=unused-argument
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


@click.command(context_settings={"help_option_names": ['-h', '--help']})
@click.option('-v', '--verbose', count=True)
@click.option("--slurm", is_flag=True, help="Run experiments on slurm.")
@click.option(
    "--submit", is_flag=True, help="Submit generated slurm script via sbatch."
)
@click.option(
    "--container", is_flag=True, help="Run experiments in a container."
)
@click.option(
    "-E", "--experiment", required=True, help="The experiment to run."
)
@click.option("-p", "--pretend", is_flag=True, help="Do not run experiments.")
@click.argument("projects", nargs=-1, callback=__validate_project_parameters)
def main(
    verbose: int,
    slurm: bool,
    submit: bool,
    container: bool,
    experiment: str,
    projects: tp.List[str],
    pretend: bool,
) -> None:
    """
    Run benchbuild experiments.

    Runs on all projects in the current paper config by default. You can
    restrict this to only certain projects or even revisions using BenchBuild-
    style project selectors: <project>[@<revision>]
    """
    # pylint: disable=too-many-branches
    initialize_cli_tool()
    initialize_projects()

    bb_command_args: tp.List[str] = ["--force-watch-unbuffered"]
    bb_extra_args: tp.List[str] = []

    if sys.stdout.isatty():
        bb_command_args.append("--force-tty")

    if verbose:
        bb_command_args.append("-" + ("v" * verbose))

    if pretend:
        click.echo("Running in pretend mode. No experiments will be executed.")
        # benchbuild only supports pretend in the normal run command
        slurm = False
        container = False

    if slurm:
        bb_command_args.append("slurm")

    if container:
        if slurm:
            if not __is_slurm_prepared():
                click.echo(
                    "It seems like benchbuild is not properly "
                    "configured for slurm + containers. "
                    "Please run 'vara-container prepare-slurm' first."
                )
                sys.exit(1)
            bb_extra_args = ["--", "container", "run"]
            if bb_cfg()["container"]["import"].value:
                bb_extra_args.append("--import")
        else:
            bb_command_args.append("container")

    if not slurm:
        bb_command_args.append("run")

    if pretend:
        bb_command_args.append("-p")

    if not projects:
        projects = list({
            cs.project_name for cs in get_paper_config().get_all_case_studies()
        })

    bb_args = list(
        itertools.chain(
            bb_command_args, ["-E", experiment], projects, bb_extra_args
        )
    )

    with local.cwd(vara_cfg()["benchbuild_root"].value):
        try:
            with benchbuild[bb_args].bgrun(stdout=PIPE, stderr=PIPE) as bb_proc:
                try:
                    _, stdout, _ = tee(bb_proc)
                except KeyboardInterrupt:
                    # wait for BB to complete when Ctrl-C is pressed
                    retcode, _, _ = tee(bb_proc)
                    sys.exit(retcode)
        except ProcessExecutionError:
            sys.exit(1)

    if slurm:
        match = __SLURM_SCRIPT_PATTERN.search(stdout)
        if match:
            slurm_script = match.group(1)
            if submit:
                click.echo(
                    f"Submitting slurm script via sbatch: {slurm_script}"
                )
                sbatch(slurm_script)
            else:
                click.echo(
                    f"Run the following command to submit the slurm:\n"
                    f"sbatch {slurm_script}"
                )
        else:
            click.echo("Could not find slurm script.")
            sys.exit(1)


def __is_slurm_prepared() -> bool:
    """Check whether the slurm/container setup seems to be configured
    properly."""
    if not bb_cfg()["container"]["root"].value:
        return False
    if not Path(bb_cfg()["slurm"]["template"].value).exists():
        return False
    return True


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter

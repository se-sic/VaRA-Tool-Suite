"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import logging
import typing as tp
from pathlib import Path

import click
import jinja2
from benchbuild.utils.settings import ConfigPath

from varats.containers.containers import (
    create_base_images,
    ImageBase,
    delete_base_images,
    export_base_images,
)
from varats.tools.tool_util import get_supported_research_tool_names
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.click_param_types import EnumChoice
from varats.utils.settings import vara_cfg, save_config, bb_cfg, save_bb_config

LOG = logging.Logger(__name__)


@click.group(
    help="Manage base container images.",
    context_settings={"help_option_names": ['-h', '--help']}
)
def main() -> None:
    """Manage base container images."""
    initialize_cli_tool()
    bb_cfg()


@main.command(help="Build base containers for the current research tool.")
@click.option(
    "--debug", is_flag=True, help="Debug failed image builds interactively."
)
@click.option(
    "--export", is_flag=True, help="Export the built images to the filesystem."
)
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumChoice(ImageBase),
    multiple=True,
    help="Only build the given image."
)
def build(images: tp.List[ImageBase], export: bool, debug: bool) -> None:
    """
    Build base containers for the current research tool.

    Args:
        images: the images to build; build all if empty
        export: if ``True``, export the built images to the filesystem
        debug: if ``True``, debug failed image builds interactively
    """
    __build_images(images, export, debug)


@main.command(help="Delete base containers for the current research tool.")
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumChoice(ImageBase),
    multiple=True,
    help="Only delete the given image. Can be given multiple times."
)
def delete(images: tp.List[ImageBase]) -> None:
    """
    Delete base containers for the current research tool.

    Args:
        images: the images to delete; delete all if empty
    """
    if images:
        delete_base_images(images)
    else:
        delete_base_images()


@main.command(help="Select the research tool to be used in base containers.")
@click.option(
    "-t",
    "--tool",
    type=click.Choice([*get_supported_research_tool_names(), "none"]),
    default=lambda: vara_cfg()["container"]["research_tool"].value or "none",
    prompt="Select a research tool to activate.",
    help="The research tool to activate."
)
def select(tool: str) -> None:
    """
    Select the research tool to be used in base containers.

    Args:
        tool: the research tool to activate
    """
    __set_research_tool(tool)


@main.command(
    help="Prepare everything necessary to run BenchBuild experiments "
    "with containers via slurm."
)
@click.option(
    "--debug", is_flag=True, help="Debug failed image builds interactively."
)
@click.option(
    "--node-dir",
    type=click.Path(path_type=Path),
    prompt="What should be the base directory on slurm nodes?",
    default=lambda: str(bb_cfg()["slurm"]["node_dir"].value),
    help="Base directory on slurm nodes. \n"
    "Must be creatable and writeable on every slurm node and your local "
    "machine and must not be on a NFS."
)
@click.option(
    "--export-dir",
    type=click.Path(path_type=Path),
    prompt="Where should container base images be exported to for storage?",
    default=lambda: str(bb_cfg()["container"]["export"].value),
    help="Base image export directory. \n"
    "Must be accessible by this machine and all slurm nodes."
)
@click.option(
    "-t",
    "--tool",
    type=click.Choice([*get_supported_research_tool_names(), "none"]),
    default=lambda: vara_cfg()["container"]["research_tool"].value or "none",
    prompt="What research tool does your experiment need?",
    help="The research tool needed by your experiment."
)
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumChoice(ImageBase),
    multiple=True,
    help="Only build the given image. \nCan be given multiple times."
)
def prepare_slurm(
    images: tp.List[ImageBase], tool: str, export_dir: Path, node_dir: Path,
    debug: bool
) -> None:
    """
    Prepare everything necessary to run BenchBuild experiments with containers
    via slurm.

    Args:
        images: the images to build; build all if empty
        tool: the research tool to use
        export_dir: the directory to export container images to
        node_dir: the base directory on slurm nodes
        debug: if ``True``, debug failed image builds interactively
    """
    click.echo("Preparing BenchBuild config.")
    template_path = Path(
        str(vara_cfg()["benchbuild_root"])
    ) / "slurm_container.sh.inc"
    bb_cfg()["slurm"]["template"] = str(template_path)
    bb_cfg()["slurm"]["node_dir"] = ConfigPath(str(node_dir))

    bb_cfg()["container"]["root"] = ConfigPath(f"{node_dir}/containers/lib")
    bb_cfg()["container"]["runroot"] = ConfigPath(f"{node_dir}/containers/run")
    bb_cfg()["container"]["export"] = ConfigPath(str(export_dir))
    bb_cfg()["container"]["import"] = ConfigPath(str(export_dir))

    if not export_dir.exists():
        LOG.info(f"Creating container export directory at {export_dir}")
        export_dir.mkdir(parents=True)

    save_bb_config()

    click.echo("Preparing slurm script template.")
    __set_research_tool(tool)
    __render_slurm_script_template(
        template_path, [repr(vara_cfg()["container"]["research_tool"])]
    )

    click.echo("Building base images. This could take a while...")
    __build_images(images, True, debug)
    click.echo("Done.")

    click.echo(
        "Run `vara-run --container --slurm -E <experiment> <project> "
        "to generate a slurm script."
    )


def __build_images(
    images: tp.List[ImageBase], export: bool, debug: bool
) -> None:
    bb_cfg()["container"]["keep"] = debug

    if images:
        create_base_images(images)
        if export:
            export_base_images(images)
    else:
        create_base_images()
        if export:
            export_base_images()


def __set_research_tool(tool: str) -> None:
    vara_cfg()["container"]["research_tool"] = None if tool == "none" else tool
    save_config()


def __render_slurm_script_template(
    output_path: Path, env_vars: tp.List[str]
) -> None:
    loader = jinja2.PackageLoader('varats.tools', 'templates')
    env = jinja2.Environment(
        trim_blocks=True, lstrip_blocks=True, loader=loader
    )
    template = env.get_template("slurm_container.sh.inc")

    with open(output_path, 'w') as slurm2:
        slurm2.write(
            template.render(vara_config=[f"export {x}" for x in env_vars])
        )


if __name__ == '__main__':
    main()

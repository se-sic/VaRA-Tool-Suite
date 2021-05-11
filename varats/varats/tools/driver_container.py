"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import typing as tp
from pathlib import Path

import click
import jinja2

from varats.containers.containers import (
    create_base_images,
    ImageBase,
    delete_base_images,
    export_base_images,
)
from varats.tools.bb_config import load_bb_config
from varats.tools.tool_util import get_supported_research_tool_names
from varats.utils.cli_util import initialize_cli_tool, EnumType
from varats.utils.settings import vara_cfg, save_config, bb_cfg, save_bb_config


@click.group(
    help="Manage base container images.",
    context_settings={"help_option_names": ['-h', '--help']}
)
def main() -> None:
    initialize_cli_tool()
    load_bb_config()


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
    type=EnumType(ImageBase),
    multiple=True,
    help="Only build the given image."
)
def build(images: tp.List[ImageBase], export: bool, debug: bool) -> None:
    __build_images(images, export, debug)


@main.command(help="Delete base containers for the current research tool.")
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumType(ImageBase),
    multiple=True,
    help="Only delete the given image. Can be given multiple times."
)
def delete(images: tp.List[ImageBase]) -> None:
    if images:
        delete_base_images(images)
    else:
        delete_base_images()


@main.command(help="Select the research tool to be used in base containers.")
@click.option(
    "-t",
    "--tool",
    type=click.Choice([*get_supported_research_tool_names(), "none"]),
    prompt="Select a research tool to activate.",
    help="The research tool to activate"
)
def select(tool: str) -> None:
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
    type=click.Path(),
    prompt="What should be the base directory on slurm nodes?",
    help="Base directory on slurm nodes. \n"
    "Must be creatable and writeable on every slurm node and your local "
    "machine and must not be on a NFS."
)
@click.option(
    "--export-dir",
    type=click.Path(),
    prompt="Where should base images be exported to for storage?",
    help="Base image export directory. \n"
    "Must be accessible by this machine and all slurm nodes."
)
@click.option(
    "-t",
    "--tool",
    type=click.Choice([*get_supported_research_tool_names(), "none"]),
    prompt="What research tool does your experiment need?",
    help="The research tool needed by your experiment."
)
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumType(ImageBase),
    multiple=True,
    help="Only build the given image. \nCan be given multiple times."
)
def prepare_slurm(
    images: tp.List[ImageBase], tool: str, export_dir: str, node_dir: str,
    debug: bool
) -> None:
    click.echo("Preparing BenchBuild config.")
    template_path = Path(
        str(vara_cfg()["benchbuild_root"])
    ) / "slurm_container.sh.inc"
    bb_cfg()["slurm"]["template"] = str(template_path)
    bb_cfg()["slurm"]["node_dir"] = node_dir

    bb_cfg()["container"]["root"] = f"{node_dir}/containers/lib"
    bb_cfg()["container"]["runroot"] = f"{node_dir}/containers/run"
    bb_cfg()["container"]["export"] = export_dir
    bb_cfg()["container"]["import"] = export_dir

    save_bb_config()

    click.echo("Preparing slurm script template.")
    __set_research_tool(tool)
    __render_slurm_script_template(
        template_path, [repr(vara_cfg()["container"]["research_tool"])]
    )

    click.echo("Building base images. This could take a while...")
    # TODO: clean exported images if present
    __build_images(images, True, debug)
    click.echo("Done.")

    click.echo(
        "Run `benchbuild slurm -E <report_type> <project> -- "
        "container run --import` inside the `benchbuild` directory "
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
    if tool == "none":
        tool = None
    vara_cfg()["container"]["research_tool"] = tool
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

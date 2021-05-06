"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import typing as tp

import click

from varats.containers.containers import (
    create_base_images,
    ImageBase,
    create_base_image,
    delete_base_image,
    delete_base_images,
    export_base_image,
    export_base_images,
)
from varats.tools.bb_config import load_bb_config
from varats.tools.tool_util import get_supported_research_tool_names
from varats.utils.cli_util import initialize_cli_tool, cli_list_choice, EnumType
from varats.utils.settings import vara_cfg, save_config, bb_cfg


@click.group(help="Manage base container images.")
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
    type=EnumType(ImageBase),
    help="Only build the given image."
)
def build(image: tp.Optional[ImageBase], export: bool, debug: bool) -> None:
    bb_cfg()["container"]["keep"] = debug

    if image:
        create_base_image(image)
        if export:
            export_base_image(image)
    else:
        create_base_images()
        if export:
            export_base_images()


@main.command(help="Delete base containers for the current research tool.")
@click.option(
    "-i",
    "--image",
    type=EnumType(ImageBase),
    help="Only delete the given image."
)
def delete(image: ImageBase) -> None:
    if image:
        delete_base_image(image)
    else:
        delete_base_images()


@main.command(help="Select the research tool to be used in base containers.")
@click.option(
    "-t",
    "--tool",
    type=click.Choice(get_supported_research_tool_names()),
    prompt="Select a research tool to activate.",
    help="The research tool to activate"
)
def select(tool) -> None:
    vara_cfg()["container"]["research_tool"] = tool
    save_config()


if __name__ == '__main__':
    main()

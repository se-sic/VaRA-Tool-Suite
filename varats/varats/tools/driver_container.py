"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import logging
import typing as tp

import click

from varats.containers.containers import (
    create_base_images,
    ImageBase,
    delete_base_images,
    export_base_images,
    ImageStage,
    delete_dev_images,
)
from varats.tools.research_tools.vara_manager import BuildType
from varats.tools.tool_util import get_supported_research_tool_names
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.click_param_types import EnumChoice
from varats.utils.settings import vara_cfg, save_config, bb_cfg

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
    "--force-rebuild",
    is_flag=True,
    help="Rebuild all stages of the base image even if they already exist."
)
@click.option(
    "--update-tool-suite",
    is_flag=True,
    help="Only update the tool suite. Implies --update-research-tool and "
    "--update-config."
)
@click.option(
    "--update-research-tool",
    is_flag=True,
    help="Only update the research tool. Implies --update config."
)
@click.option("--update-config", is_flag=True, help="Only update the config.")
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumChoice(ImageBase),
    multiple=True,
    help="Only build the given image."
)
def build(
    images: tp.List[ImageBase], force_rebuild: bool, update_config: bool,
    update_research_tool: bool, update_tool_suite: bool, export: bool,
    debug: bool
) -> None:
    """
    Build base containers for the current research tool.

    Args:
        images: the images to build; build all if empty
        export: if ``True``, export the built images to the filesystem
        debug: if ``True``, debug failed image builds interactively
    """
    stage = ImageStage.STAGE_00_BASE

    if update_tool_suite:
        stage = ImageStage.STAGE_10_VARATS
    elif update_research_tool:
        stage = ImageStage.STAGE_20_TOOL
    elif update_config:
        stage = ImageStage.STAGE_30_CONFIG

    bb_cfg()["container"]["keep"] = debug
    if images:
        create_base_images(images, stage, force_rebuild)
        if export:
            export_base_images(images)
    else:
        create_base_images(stage=stage, force_rebuild=force_rebuild)
        if export:
            export_base_images()


@main.command(help="Delete base containers for the current research tool.")
@click.option(
    "--build-type",
    type=EnumChoice(BuildType, case_sensitive=False),
    help="If present, delete the dev images for the current research tool "
    "and the given build type."
)
@click.option(
    "-i",
    "--image",
    "images",
    type=EnumChoice(ImageBase),
    multiple=True,
    help="Only delete the given image. Can be given multiple times."
)
def delete(
    images: tp.List[ImageBase], build_type: tp.Optional[BuildType]
) -> None:
    """
    Delete base containers for the current research tool.

    Args:
        images: the images to delete; delete all if empty
        build_type: if present delete dev images for the current research tool
                    and the given build type
    """
    if build_type:
        if images:
            delete_dev_images(build_type, images)
        else:
            delete_dev_images(build_type)
    else:
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
    vara_cfg()["container"]["research_tool"] = None if tool == "none" else tool
    save_config()


if __name__ == '__main__':
    main()

"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import argparse
import typing as tp

from argparse_utils import enum_action

from varats.containers.containers import (
    create_base_images,
    ImageBase,
    create_base_image,
    delete_base_image,
    delete_base_images,
)
from varats.tools.bb_config import load_bb_config
from varats.tools.tool_util import get_supported_research_tool_names
from varats.utils.cli_util import initialize_cli_tool, cli_list_choice
from varats.utils.settings import vara_cfg, save_config


def main() -> None:
    """
    Main function for managing container related functionality.

    `vara-container`
    """
    initialize_cli_tool()
    load_bb_config()

    parser = argparse.ArgumentParser("vara-container")
    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-container build
    build_parser = sub_parsers.add_parser(
        'build',
        help="Build base containers for the current research tool."
        "By default builds all base containers."
    )
    build_parser.add_argument(
        "-i",
        "--image",
        help="Only build the given image",
        action=enum_action(ImageBase)
    )

    # vara-container delete
    delete_parser = sub_parsers.add_parser(
        'delete',
        help="Delete base containers for the current research tool."
        "By default deletes all base containers."
    )
    delete_parser.add_argument(
        "-i",
        "--image",
        help="Only delete the given image",
        action=enum_action(ImageBase)
    )

    # vara-container select-tool
    sub_parsers.add_parser(
        'select-tool',
        help="Select the research tool to be used in base containers."
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'build':
        __container_build(args)
    elif args['subcommand'] == 'delete':
        __container_delete(args)
    elif args['subcommand'] == 'select-tool':
        __select_research_tool()


def __container_build(args: tp.Dict[str, tp.Any]) -> None:
    if "image" in args.keys():
        create_base_image(args["image"])
    else:
        create_base_images()


def __container_delete(args: tp.Dict[str, tp.Any]) -> None:
    if "image" in args.keys():
        delete_base_image(args["image"])
    else:
        delete_base_images()


def __select_research_tool() -> None:

    def set_research_tool(tool: str) -> None:
        vara_cfg()["container"]["research_tool"] = tool
        save_config()

    current_tool = vara_cfg()["container"]["research_tool"].value
    cli_list_choice(
        "Choose a number to select a research tool",
        get_supported_research_tool_names(), lambda x: f"{x} *"
        if current_tool and x == current_tool else x, set_research_tool
    )


if __name__ == '__main__':
    main()

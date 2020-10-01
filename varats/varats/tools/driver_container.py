"""
Driver module for `vara-container`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import argparse

from varats.containers.containers import create_base_images
from varats.tools.bb_config import load_bb_config
from varats.utils.cli_util import initialize_cli_tool


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
    sub_parsers.add_parser(
        'build',
        help="Build all base containers for the current research tool."
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'build':
        __container_build()


def __container_build() -> None:
    create_base_images()


if __name__ == '__main__':
    main()

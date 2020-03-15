"""
Driver module for `vara-pc`.

This module provides a command line interface for creating and managing paper
configs.
"""

import typing as tp
import argparse
from pathlib import Path

from varats.settings import CFG, save_config


def main() -> None:
    """
    Main function for working with paper configs.

    `vara-pc`
    """
    parser = argparse.ArgumentParser("vara-pc")

    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-pc create
    create_parser = sub_parsers.add_parser('create',
                                           help="Create a new paper config.")
    create_parser.add_argument("paper_config",
                               help="Path to the new paper config. Relative "
                               "paths are interpreted relative to the current "
                               "`paper_config/folder`.",
                               type=str)

    # vara-pc set
    set_parser = sub_parsers.add_parser('select',
                                        help="Select the current paper config.")
    set_parser.add_argument("paper_config",
                            help="Path paper config to select as the current "
                            "one. Relative paths are interpreted relative to "
                            "the current `paper_config/folder`.",
                            type=str)

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'create':
        __pc_create(args)
    elif args['subcommand'] == 'select':
        __pc_set(args)


def __pc_create(args: tp.Dict[str, tp.Any]) -> None:
    pc_path = Path(args['paper_config'])

    if not pc_path.is_absolute():
        current_folder = CFG["paper_config"]["folder"].value
        if current_folder is None:
            pc_path = Path(
                CFG["config_file"].value).parent / "paper_configs" / pc_path
        else:
            pc_path = Path(current_folder) / pc_path

    if pc_path.exists():
        print(f"Cannot create paper config at: {pc_path} "
              "(Path already exists).")

    folder = pc_path.parent
    current_config = pc_path.name

    print(f"Creating new paper config {current_config} at location {folder}.")
    pc_path.mkdir(parents=True)

    CFG["paper_config"]["folder"] = str(folder)
    CFG["paper_config"]["current_config"] = str(current_config)
    save_config()


def __pc_set(args: tp.Dict[str, tp.Any]) -> None:
    pc_path = Path(args['paper_config'])

    if not pc_path.is_absolute():
        pc_path = Path(CFG["paper_config"]["folder"].value) / pc_path

    if not (pc_path.exists() and pc_path.is_dir()):
        print(f"Not a paper config: {pc_path} "
              "(Path does not exist or is no directory).")

    folder = pc_path.parent
    current_config = pc_path.name

    print(f"Current paper config is now {current_config} at location {folder}.")
    CFG["paper_config"]["folder"] = str(folder)
    CFG["paper_config"]["current_config"] = str(current_config)
    save_config()


if __name__ == '__main__':
    main()

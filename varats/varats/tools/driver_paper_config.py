"""
Driver module for `vara-pc`.

This module provides a command line interface for creating and managing paper
configs.
"""
import argparse
import logging
import typing as tp
from pathlib import Path

from varats.paper.paper_config import (
    get_loaded_paper_config,
    is_paper_config_loaded,
)
from varats.utils.cli_util import cli_list_choice, initialize_cli_tool
from varats.utils.settings import (
    get_value_or_default,
    get_varats_base_folder,
    save_config,
    vara_cfg,
)

LOG = logging.getLogger(__name__)


def _set_paper_config_parser_arg(
    parser: argparse.ArgumentParser, opt: bool = False
) -> None:
    config_opt_name = "paper_config" if not opt else "--paper-config"
    parser.add_argument(
        config_opt_name,
        help="Path to the new paper config. Relative "
        "paths are interpreted relative to the current "
        "`paper_config/folder`.",
        type=str
    )


def main() -> None:
    """
    Main function for working with paper configs.

    `vara-pc`
    """
    initialize_cli_tool()
    parser = argparse.ArgumentParser("vara-pc")

    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-pc create
    create_parser = sub_parsers.add_parser(
        'create', help="Create a new paper config."
    )
    _set_paper_config_parser_arg(create_parser)

    # vara-pc set
    set_parser = sub_parsers.add_parser(
        'select', help="Select the current paper config."
    )
    _set_paper_config_parser_arg(set_parser, True)

    # vara-pc list
    list_parser = sub_parsers.add_parser(
        'list', help="List all available paper configs"
    )
    list_parser.add_argument(
        "--paper-config-path",
        help="Path to the paper config folder.",
        type=Path
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if vara_cfg()["paper_config"]["folder"].value is None:
        # Setup default paper config path when none exists
        vara_cfg()["paper_config"]["folder"] = str(
            Path('paper_configs').absolute()
        )
        save_config()

    if args['subcommand'] == 'create':
        __pc_create(args)
    elif args['subcommand'] == 'select':
        __pc_set(args)
    elif args['subcommand'] == 'list':
        __pc_list(args)


def __get_paper_configs(pc_folder_path: Path) -> tp.List[str]:
    paper_configs: tp.List[str] = []
    for folder in pc_folder_path.iterdir():
        paper_configs.append(folder.name)
    return paper_configs


def __pc_create(args: tp.Dict[str, tp.Any]) -> None:
    pc_path = Path(args['paper_config'])
    if not pc_path.is_absolute():
        current_folder = vara_cfg()["paper_config"]["folder"].value
        if current_folder is None:
            pc_path = Path(
                vara_cfg()["config_file"].value
            ).parent / "paper_configs" / pc_path
        else:
            pc_path = Path(current_folder) / pc_path

    if pc_path.exists():
        LOG.error(
            f"Cannot create paper config at: {pc_path} "
            "(Path already exists)."
        )
        return

    folder = pc_path.parent
    current_config = pc_path.name

    LOG.info(
        f"Creating new paper config {current_config} at location {folder}."
    )
    pc_path.mkdir(parents=True)

    vara_cfg()["paper_config"]["folder"] = str(folder)
    vara_cfg()["paper_config"]["current_config"] = str(current_config)
    save_config()


def __pc_set(args: tp.Dict[str, tp.Any]) -> None:
    if 'paper_config' in args:
        pc_path = Path(args['paper_config'])
    else:
        pc_folder_path = Path(
            get_value_or_default(
                vara_cfg()["paper_config"], "folder",
                str(get_varats_base_folder())
            )
        )
        if not (pc_folder_path.exists() and pc_folder_path.is_dir()):
            LOG.error(
                f"Paper config folder not set: {pc_folder_path} "
                "(Path does not exist or is no directory)."
            )
            return

        paper_configs = __get_paper_configs(pc_folder_path)
        if not paper_configs:
            LOG.error(f"Could not find paper configs in: {pc_folder_path}")
            return

        raw_pc_path = None

        def set_pc_path(choice: str) -> None:
            nonlocal raw_pc_path
            raw_pc_path = choice

        try:
            if is_paper_config_loaded():
                current_config: tp.Optional[str] = get_loaded_paper_config(
                ).path.name
            else:
                current_config = None

            cli_list_choice(
                "Choose a number to select a paper config", paper_configs,
                lambda x: f"{x} *"
                if current_config and x == current_config else x, set_pc_path
            )
        except EOFError:
            return
        if raw_pc_path is None:
            raise AssertionError("Choice should always return a value")
        pc_path = Path(raw_pc_path)

    if not pc_path.is_absolute():
        pc_path = Path(vara_cfg()["paper_config"]["folder"].value) / pc_path

    if not (pc_path.exists() and pc_path.is_dir()):
        LOG.error(
            f"Not a paper config: {pc_path} "
            "(Path does not exist or is no directory)."
        )
        return

    folder = pc_path.parent
    current_config = pc_path.name

    LOG.info(
        f"Current paper config is now {current_config} at location {folder}."
    )
    vara_cfg()["paper_config"]["folder"] = str(folder)
    vara_cfg()["paper_config"]["current_config"] = str(current_config)
    save_config()


def __pc_list(args: tp.Dict[str, tp.Any]) -> None:
    if "paper_config_path" in args:
        pc_folder_path = Path(args['paper_config_path'])
    else:
        pc_folder_path = Path(vara_cfg()["paper_config"]["folder"].value)

    if not (pc_folder_path.exists() and pc_folder_path.is_dir()):
        LOG.error(
            f"Paper config folder not found: {pc_folder_path} "
            "(Path does not exist or is no directory)."
        )
        return

    print("Found the following paper_configs:")
    if is_paper_config_loaded():
        current_config: tp.Optional[str] = get_loaded_paper_config().path.name
    else:
        current_config = None

    for paper_config in __get_paper_configs(pc_folder_path):
        if current_config and paper_config == current_config:
            print(f"{paper_config} *")
        else:
            print(paper_config)


if __name__ == '__main__':
    main()

"""
Driver module for `vara-pc`.

This module provides a command line interface for creating and managing paper
configs.
"""
import logging
import typing as tp
from pathlib import Path

import click

from varats.paper_mgmt.paper_config import get_paper_config
from varats.ts_utils.cli_util import cli_list_choice, initialize_cli_tool
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.settings import (
    get_value_or_default,
    get_varats_base_folder,
    save_config,
    vara_cfg,
)

LOG = logging.getLogger(__name__)


@click.group("vara-pc")
def main() -> None:
    """
    Main function for working with paper configs.

    `vara-pc`
    """
    initialize_cli_tool()

    if vara_cfg()["paper_config"]["folder"].value is None:
        # Setup default paper config path when none exists
        vara_cfg()["paper_config"]["folder"] = str(
            Path('paper_configs').absolute()
        )
        save_config()


def _get_paper_configs(pc_folder_path: Path) -> tp.List[str]:
    paper_configs: tp.List[str] = []
    for folder in pc_folder_path.iterdir():
        paper_configs.append(folder.name)
    return sorted(paper_configs)


@main.command("create")
@click.argument("paper_config", type=click.Path())
def _pc_create(paper_config: str) -> None:
    """paper_config:
            Path to the new paper config.
             Relative paths are interpreted relative to the current
             `paper_config/folder`."""
    pc_path: Path = Path(paper_config)
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


@main.command("select")
@click.option("--paper-config", type=click.Path())
def _pc_set(paper_config: tp.Optional[Path]) -> None:
    if not paper_config:
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

        paper_configs = _get_paper_configs(pc_folder_path)
        if not paper_configs:
            LOG.error(f"Could not find paper configs in: {pc_folder_path}")
            return

        raw_pc_path = None

        def set_pc_path(choice: str) -> None:
            nonlocal raw_pc_path
            raw_pc_path = choice

        current_config = None
        try:
            current_config = get_paper_config().path.name
        except ConfigurationLookupError:
            # No paper config specified in the varats config file
            pass

        try:
            cli_list_choice(
                "Choose a number to select a paper config", paper_configs,
                lambda x: f"{x} *"
                if current_config and x == current_config else x, set_pc_path
            )
        except EOFError:
            return
        if raw_pc_path is None:
            raise AssertionError("Choice should always return a value")
        paper_config = Path(raw_pc_path)

    paper_config = Path(paper_config)
    if not paper_config.is_absolute():
        paper_config = Path(
            vara_cfg()["paper_config"]["folder"].value
        ) / paper_config

    if not (paper_config.exists() and paper_config.is_dir()):
        LOG.error(
            f"Not a paper config: {paper_config} "
            "(Path does not exist or is no directory)."
        )
        return

    folder = paper_config.parent
    current_config = paper_config.name

    LOG.info(
        f"Current paper config is now {current_config} at location {folder}."
    )
    vara_cfg()["paper_config"]["folder"] = str(folder)
    vara_cfg()["paper_config"]["current_config"] = str(current_config)
    save_config()


@main.command("list")
@click.option(
    "--paper-config-path",
    help="Path to the paper config folder.",
    type=click.Path()
)
def _pc_list(paper_config_path: tp.Optional[Path]) -> None:
    if not paper_config_path:
        paper_config_path = Path(vara_cfg()["paper_config"]["folder"].value)

    if not (paper_config_path.exists() and paper_config_path.is_dir()):
        LOG.error(
            f"Paper config folder not found: {paper_config_path} "
            "(Path does not exist or is no directory)."
        )
        return

    print("Found the following paper_configs:")
    current_config = None
    try:
        current_config = get_paper_config().path.name
    except ConfigurationLookupError:
        # No paper config specified in the varats config file
        pass

    for paper_config in _get_paper_configs(paper_config_path):
        if current_config and paper_config == current_config:
            print(f"{paper_config} *")
        else:
            print(paper_config)


if __name__ == '__main__':
    main()

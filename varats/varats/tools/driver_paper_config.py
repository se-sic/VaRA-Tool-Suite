"""
Driver module for `vara-pc`.

This module provides a command line interface for creating and managing paper
configs.
"""
import logging
import typing as tp
from pathlib import Path

import click
from trogon import tui

from varats.paper.paper_config import get_paper_config
from varats.ts_utils.cli_util import cli_list_choice, initialize_cli_tool
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.settings import (
    get_value_or_default,
    get_varats_base_folder,
    save_config,
    vara_cfg,
)

LOG = logging.getLogger(__name__)


@tui()  # type: ignore
@click.group("vara-pc")
def main() -> None:
    """
    Main function for working with paper configs.

    `vara-pc`
    """
    initialize_cli_tool()


def _get_paper_configs() -> tp.List[str]:
    paper_configs: tp.List[str] = []
    for folder in Path(vara_cfg()["paper_config"]["folder"].value).iterdir():
        paper_configs.append(folder.name)
    return sorted(paper_configs)


@main.command("create")  # type: ignore
@click.argument("paper_config")
def _pc_create(paper_config: str) -> None:
    """Create a new paper config."""
    pc_folder_path = Path(vara_cfg()["paper_config"]["folder"].value)
    pc_path = pc_folder_path / paper_config

    if pc_path.exists():
        LOG.error(
            f"Cannot create paper config at: {pc_path} (Path already exists)."
        )
        return

    LOG.info(f"Creating new paper config {paper_config} at location {pc_path}.")
    pc_path.mkdir(parents=True)

    # automatically select new paper config
    vara_cfg()["paper_config"]["current_config"] = paper_config
    save_config()


def create_pc_choice() -> click.Choice:
    paper_configs = _get_paper_configs()
    return click.Choice(paper_configs)


@main.command("select")  # type: ignore
@click.option("--paper-config", type=create_pc_choice(), required=True)
def _pc_set(paper_config: tp.Optional[str]) -> None:
    if not paper_config:
        pc_folder_path = Path(vara_cfg()["paper_config"]["folder"].value)

        paper_configs = _get_paper_configs()
        if not paper_configs:
            LOG.error(f"Could not find any paper configs.")
            return

        selected_paper_config = None

        def set_pc_path(choice: str) -> None:
            nonlocal selected_paper_config
            selected_paper_config = choice

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
        if selected_paper_config is None:
            raise AssertionError("Choice should always return a value")
        paper_config = selected_paper_config

    LOG.info(f"Current paper config is now {paper_config}.")
    vara_cfg()["paper_config"]["current_config"] = paper_config
    save_config()


@main.command("list")  # type: ignore
def _pc_list() -> None:
    print("Found the following paper_configs:")
    current_config = None
    try:
        current_config = get_paper_config().path.name
    except ConfigurationLookupError:
        # No paper config specified in the varats config file
        pass

    for paper_config in _get_paper_configs():
        if current_config and paper_config == current_config:
            print(f"{paper_config} *")
        else:
            print(paper_config)


if __name__ == '__main__':
    main()

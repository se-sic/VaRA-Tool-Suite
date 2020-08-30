"""Command line utilities."""

import logging
import os
import typing as tp
from pathlib import Path

from rich.traceback import install

from varats.tools.research_tools.phasar import Phasar
from varats.tools.research_tools.research_tool import ResearchTool
from varats.tools.research_tools.vara import VaRA
from varats.utils.settings import vara_cfg


def cli_yn_choice(question: str, default: str = 'y') -> bool:
    """Ask the user to make a y/n decision on the cli."""
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice: str = str(
        input(
            "{message} ({choices}) ".format(message=question, choices=choices)
        )
    )
    values: tp.Union[tp.Tuple[str, str],
                     tp.Tuple[str, str,
                              str]] = ('y', 'yes', ''
                                      ) if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values


ListType = tp.TypeVar("ListType")


def cli_list_choice(
    question: str,
    choices: tp.List[ListType],
    choice_to_str: tp.Callable[[ListType], str],
    on_choice_callback: tp.Callable[[ListType], None],
    start_label: int = 0,
    default: int = 0,
    repeat: bool = False
) -> None:
    """
    Ask the user to select an item from a list on the cli.

    Args:
        question: the question to ask the user
        choices: the choices the user has
        choice_to_str: a function converting a choice to a string
        on_choice_callback: action to perform when a choice has been made
        start_label: the number label of the first choice
        default: the default choice that is taken if no input is given
        repeat: whether to ask for another choice after ``on_choice_callback``
                has finished
    """
    if repeat:
        prompt = f"{question} or enter 'q' to quit (default={default}): "
    else:
        prompt = f"{question} (default={default}): "

    max_idx_digits = len(str(len(choices) - 1))
    for idx, choice in enumerate(choices, start=start_label):
        idx_str = f"{idx}.".ljust(max_idx_digits + 1, " ")
        print(f"{idx_str} {choice_to_str(choice)}")

    user_choice = input(prompt)
    while not user_choice.startswith("q"):
        if not user_choice:
            user_choice = str(default)
        if user_choice.isdigit(
        ) and start_label <= int(user_choice) < start_label + len(choices):
            on_choice_callback(choices[int(user_choice) - start_label])
        if not repeat:
            return
        user_choice = input(prompt)


def initialize_cli_tool() -> None:
    """Initializes all relevant context and tools for varats cli tools."""
    install(width=120)
    initialize_logger_config()


def initialize_logger_config() -> None:
    """Initializes the logging framework with a basic config, allowing the user
    to pass the warning level via an environment variable ``LOG_LEVEL``."""
    log_level = os.environ.get('LOG_LEVEL', "WARNING").upper()
    logging.basicConfig(level=log_level)


def get_research_tool_type(
    name: str
) -> tp.Union[tp.Type[VaRA], tp.Type[Phasar]]:
    """
    Look up the type of a research tool by name.

    Args:
        name: of the research tool

    Returns: the research tool type corresponding to ``name``
    """
    if name in ("VaRA", "vara"):
        return VaRA

    if name == "phasar":
        return Phasar

    raise LookupError(f"Could not find research tool {name}")


def get_research_tool(
    name: str,
    source_location: tp.Optional[Path] = None
) -> ResearchTool[tp.Any]:
    """
    Look up a research tool by name.

    Args:
        name: of the research tool
        source_location: of the research tool, if ``None`` is provided the
                         location saved in the config will be used

    Returns:
        the research tool with the specified ``name``,
        otherwise, raises LookupError
    """
    rs_type = get_research_tool_type(name)

    if source_location:
        src_folder = Path(source_location)
    elif rs_type.has_source_location():
        src_folder = rs_type.source_location()
    else:
        config_root_path = Path(str(vara_cfg()["config_file"])).parent
        src_folder = config_root_path / "tools_src/"

    if not src_folder.exists():
        src_folder.mkdir(parents=True)

    return rs_type(src_folder)


def get_supported_research_tool_names() -> tp.List[str]:
    """Returns a list of all supported research tools."""
    return ["phasar", "vara"]

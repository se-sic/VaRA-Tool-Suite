"""
Command line utilities.
"""

import typing as tp
import logging
import os
from pathlib import Path

from varats.tools.research_tools.research_tool import ResearchTool
from varats.tools.research_tools.vara import VaRA
from varats.settings import CFG


def cli_yn_choice(question: str, default: str = 'y') -> bool:
    """
    Ask the user to make a y/n decision on the cli.
    """
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice: str = str(
        input("{message} ({choices}) ".format(message=question,
                                              choices=choices)))
    values: tp.Union[tp.Tuple[str, str],
                     tp.Tuple[str, str,
                              str]] = ('y', 'yes',
                                       '') if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values


def cli_list_choice(question: str,
                    num_choices: int,
                    start: int = 0,
                    default: int = 0) -> tp.Optional[int]:
    """
    Ask the user to select an item from a list on the cli.

    Args:
        question: the question to ask the user
        num_choices: the number of choices the user has
        start: the number of the first choice
        default: the default choice that is taken if no input is given

    Returns:
        the user's choice, i.e., a number between ``start`` (inclusive) and
        ``start + num_choices`` (exclusive), or ``None`` for an invalid choice
    """
    choice = input(f"{question} (default={default}): ")
    if not choice:
        return default
    if choice.isdigit() and start <= int(choice) < start + num_choices:
        return int(choice)
    return None


def initialize_logger_config() -> None:
    """
    Initializes the logging framework with a basic config, allowing the user to
    pass the warning level via an environment variable ``LOG_LEVEL``.
    """
    log_level = os.environ.get('LOG_LEVEL', "WARNING").upper()
    logging.basicConfig(level=log_level)


def get_research_tool(
        name: str,
        source_location: tp.Optional[Path] = None) -> ResearchTool[tp.Any]:
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
    if name in ("VaRA", "vara"):
        return VaRA(source_location if source_location is not None else Path(
            CFG["vara"]["llvm_source_dir"].value))

    raise LookupError(f"Could not find research tool {name}")


def get_supported_research_tool_names() -> tp.List[str]:
    """
    Returns a list of all supported research tools.
    """
    return ["VaRA", "vara"]

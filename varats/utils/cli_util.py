"""
Command line utilities.
"""

import typing as tp
import logging
import os


def cli_yn_choice(question: str, default: str = 'y') -> bool:
    """
    Ask the user to make a y/n decision on the cli.
    """
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice: str = str(
        input("{message} ({choices}) ".format(message=question,
                                              choices=choices)))
    values: tp.Union[tp.Tuple[str, str], tp.Tuple[str, str, str]] = (
        'y', 'yes', '') if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values


def initialize_logger_config() -> None:
    """
    Initializes the logging framework with a basic config, allowing the user to
    pass the warning level via an environment variable ``LOG_LEVEL``.
    """
    log_level = os.environ.get('LOG_LEVEL', "WARNING").upper()
    logging.basicConfig(level=log_level)


def log_without_linsep(log_func: tp.Callable[[str], None]
                      ) -> tp.Callable[[str], None]:
    """
    Wraps the logger function and strips away all trailing whitespace and
    newline characters, making logs more reable, e.g., for bash and command
    line tool output.
    """
    return lambda x: log_func(x.rstrip())

"""
Command line utilities.
"""

import typing as tp


def cli_yn_choice(question, default='y') -> bool:
    """
    Ask the user to make a y/n decision on the cli.
    """
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice: str = str(
        input("{message} ({choices}) ".format(
            message=question, choices=choices)))
    values: tp.Union[tp.Tuple[str, str], tp.Tuple[str, str, str]] = (
        'y', 'yes', '') if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values

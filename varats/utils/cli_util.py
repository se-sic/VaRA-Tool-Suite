"""
Command line utilities.
"""


def cli_yn_choice(question, default='y') -> bool:
    """
    Ask the user to make a y/n decision on the cli.
    """
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice = input("{message} ({choices}) ".format(
        message=question,
        choices=choices
    ))
    values = ('y', 'yes', '') if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values

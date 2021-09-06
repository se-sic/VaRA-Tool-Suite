"""Command line utilities."""

import logging
import os
import typing as t
import typing as tp
from enum import Enum

import click
from click import Context, Parameter
from rich.traceback import install


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


CLIOptionTy = tp.Callable[..., tp.Any]


# TODO: make this have a typed version of the click.core.Option constructor?
def make_cli_option(*param_decls: str, **attrs: tp.Any) -> CLIOptionTy:
    """
    Create an object that represents a click command line option, i.e., the
    decorator object that is created by ``click.option()``.

    Args:
        *param_decls: parameter declarations, i.e., how this option can be used
        **attrs: attributes used to construct the option

    Returns:
        a click CLI option that can be wrapped around a function
    """
    return click.option(*param_decls, **attrs)


def add_cli_options(command: tp.Callable[..., None],
                    *options: CLIOptionTy) -> tp.Callable[..., None]:
    """
    Adds click CLI options to a click command.

    Args:
        command: the command
        *options: the options to add

    Returns:
        the command with the added options
    """
    for option in options:
        command = option(command)
    return command


ChoiceTy = tp.TypeVar("ChoiceTy")


class TypedChoice(click.Choice, tp.Generic[ChoiceTy]):
    """Typed version of click's choice parameter type."""

    name = "typed choice"

    def __init__(
        self, choices: tp.Dict[str, ChoiceTy], case_sensitive: bool = True
    ):
        self.__choices = choices
        super().__init__(list(choices.keys()), case_sensitive)

    def convert(
        self, value: t.Any, param: t.Optional[Parameter],
        ctx: t.Optional[Context]
    ) -> ChoiceTy:
        return self.__choices[super().convert(value, param, ctx)]


class TypedMultiChoice(click.Choice, tp.Generic[ChoiceTy]):
    """
    Typed choice parameter type allows giving multiple values.

    Multiple values can be given as a comma separated list; no whitespace
    allowed.
    """

    name = "typed multi choice"

    def __init__(
        self,
        choices: tp.Dict[str, tp.List[ChoiceTy]],
        case_sensitive: bool = True
    ):
        # Relates to: https://thingspython.wordpress.com/2010/09/27/another
        # -super-wrinkle-raising-typeerror/
        self.as_super = super(TypedMultiChoice, self)
        self.__choices = choices
        super().__init__(list(choices.keys()), case_sensitive)

    def convert(
        self, value: t.Any, param: t.Optional[Parameter],
        ctx: t.Optional[Context]
    ) -> tp.List[ChoiceTy]:
        values = [value]
        if isinstance(value, str):
            values = value.split(",")

        return [
            item for v in values
            for item in self.__choices[self.as_super.convert(v, param, ctx)]
        ]


EnumTy = tp.TypeVar("EnumTy", bound=Enum)


class EnumChoice(click.Choice, tp.Generic[EnumTy]):
    """
    Enum choice type for click.

    This type can be used with click to specify a choice from the given enum.
    """

    def __init__(self, enum: tp.Type[EnumTy], case_sensitive: bool = True):
        self.__enum = enum
        super().__init__(list(dict(enum.__members__).keys()), case_sensitive)

    def convert(
        self, value: tp.Union[str, EnumTy], param: tp.Optional[click.Parameter],
        ctx: tp.Optional[click.Context]
    ) -> EnumTy:
        if isinstance(value, Enum):
            return value
        return self.__enum[super().convert(value, param, ctx)]

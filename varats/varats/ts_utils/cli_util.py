"""Command line utilities."""
import abc
import logging
import os
import sys
import typing as tp
from select import select

import click
from plumbum.lib import read_fd_decode_safely
from plumbum.machines.local import PlumbumLocalPopen
from rich.traceback import install

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable


def cli_yn_choice(question: str, default: str = 'y') -> bool:
    """Ask the user to make a y/n decision on the cli."""
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice: str = str(input(f"{question} ({choices}) "))
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


# ------------------------------------------------------------------------------
# CLI option declarations
# ------------------------------------------------------------------------------
CommandTy = tp.Union[tp.Callable[..., tp.Any], click.Command]
CLIOptionTy = tp.Callable[[CommandTy], CommandTy]


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


def add_cli_options(command: CommandTy, *options: CLIOptionTy) -> CommandTy:
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


# ------------------------------------------------------------------------------
# CLIOptionConverter
# ------------------------------------------------------------------------------
ConversionTy = tp.TypeVar("ConversionTy", bound=tp.Any, covariant=True)


class CLIOptionConverter(abc.ABC, tp.Generic[ConversionTy]):
    """
    Converter for CLI option declarations.

    Converters are required for CLI options that are converted to complex types
    by click so that they can still be properly stored in an artefact file.
    In general, a converter should implement a mapping from the complex type to
    a string value as it would be provided on the command line.

    A converter can be attached to a CLI option using the function/decorator
    :func:`convert_value()`.
    """

    @staticmethod
    @abc.abstractmethod
    def value_to_string(
        value: tp.Union[ConversionTy, tp.List[ConversionTy]]
    ) -> tp.Union[str, tp.List[str]]:
        """Convert a value to its string representation."""
        ...

    @staticmethod
    @abc.abstractmethod
    def string_to_value(
        str_value: tp.Union[str, tp.List[str]]
    ) -> tp.Union[ConversionTy, tp.List[ConversionTy]]:
        """Construct a value from its string representation."""
        ...


class CLIOptionWithConverter(tp.Generic[ConversionTy]):
    """Wrapper class that associates a converter with a CLI option
    declaration."""

    def __init__(
        self, name: str, converter: tp.Type[CLIOptionConverter[ConversionTy]],
        cli_decl: tp.Callable[..., CLIOptionTy]
    ):
        self.__name = name
        self.__converter = converter
        self.__cli_decl = cli_decl

    @property
    def name(self) -> str:
        return self.__name

    @property
    def converter(self) -> tp.Type[CLIOptionConverter[ConversionTy]]:
        return self.__converter

    def __call__(self, *param_decls: str, **attrs: tp.Any) -> CLIOptionTy:
        return self.__cli_decl(*param_decls, **attrs)


def convert_value(
    name: str, converter: tp.Type[CLIOptionConverter[ConversionTy]]
) -> tp.Callable[..., CLIOptionTy]:
    """
    Decorator for calls to :func:`make_cli_option()` that attaches a converter.

    Converters are required for CLI options that are converted to complex types
    by click so that they can still be properly stored in an artefact file.
    In general, a converter should implement a mapping from the complex type to
    a string value as it would be provided on the command line.

    Args:
        name: name for the CLI option. This must be the same as the name for the
              click option that it wraps but with '-' replaced by '_'.
        converter: the converter that is attached to the option

    Returns:
        a CLI option declaration that can be used as if it was created by
        :func:`make_cli_option()`
    """

    def decorator(
        cli_decl: tp.Callable[..., CLIOptionTy]
    ) -> tp.Callable[..., CLIOptionTy]:
        return CLIOptionWithConverter(name, converter, cli_decl)

    return decorator


# ------------------------------------------------------------------------------
# Plot/Table config options
# ------------------------------------------------------------------------------
OptionTy = tp.TypeVar("OptionTy")


class ConfigOption(tp.Generic[OptionTy]):
    """
    Class representing a plot/table config option.

    Values can be retrieved via the call operator.

    Args:
        name: name of the option
        help_str: help string for this option
        default: global default value for the option
        view_default: global default value when in view mode; do not pass if
                      same value is required in both modes
        value: user-provided value of the option; do not pass if not set by user
    """

    def __init__(
        self,
        name: str,
        help_str: str,
        default: OptionTy,
        view_default: tp.Optional[OptionTy] = None,
        value: tp.Optional[OptionTy] = None
    ) -> None:
        self.__name = name
        self.__metavar = name.upper()
        self.__type = type(default)
        self.__default = default
        self.__view_default = view_default
        self.__value: tp.Optional[OptionTy] = value
        self.__help = f"{help_str} (global default = {default})"

    @property
    def name(self) -> str:
        return self.__name

    @property
    def default(self) -> OptionTy:
        return self.__default

    @property
    def view_default(self) -> tp.Optional[OptionTy]:
        return self.__view_default

    @property
    def value(self) -> tp.Optional[OptionTy]:
        return self.__value

    def with_value(self, value: OptionTy) -> 'ConfigOption[OptionTy]':
        """
        Create a copy of this option with the given value.

        Args:
            value: the value for the copied option

        Returns:
            a copy of the option with the given value
        """
        return ConfigOption(
            self.name, self.__help, self.__default, self.__view_default, value
        )

    def to_cli_option(self) -> CLIOptionTy:
        """
        Create a CLI option from this option.

        Returns:
            a CLI option for this option
        """
        if self.__type is bool:
            return make_cli_option(
                f"--{self.__name.replace('_', '-')}",
                is_flag=True,
                required=False,
                help=self.__help
            )
        return make_cli_option(
            f"--{self.__name.replace('_', '-')}",
            metavar=self.__metavar,
            type=self.__type,
            required=False,
            help=self.__help
        )

    def value_or_default(
        self,
        view: bool,
        default: tp.Optional[OptionTy] = None,
        view_default: tp.Optional[OptionTy] = None
    ) -> OptionTy:
        """
        Retrieve the value for this option.

        The precedence for values is
        `user provided value > plot-specific default > global default`.

        This function can also be called via the call operator.

        Args:
            view: whether view-mode is enabled
            default: plot-specific default value
            view_default: plot-specific default value when in view-mode

        Returns:
            the value for this option
        """
        # cannot pass view_default if option has no default for view mode
        assert not (view_default and not self.__view_default)

        if self.value:
            return self.value
        if view:
            if self.__view_default:
                return view_default or self.__view_default
            return default or self.__default
        return default or self.__default

    def __str__(self) -> str:
        return f"{self.__name}[default={self.__default}, value={self.value}]"


@runtime_checkable
class COGetter(Protocol[OptionTy]):
    """Getter type for options with no view default."""

    def __call__(self, default: tp.Optional[OptionTy] = None) -> OptionTy:
        ...


@runtime_checkable
class COGetterV(Protocol[OptionTy]):
    """Getter type for options with view default."""

    def __call__(
        self,
        default: tp.Optional[OptionTy] = None,
        view_default: tp.Optional[OptionTy] = None
    ) -> OptionTy:
        ...


def tee(process: PlumbumLocalPopen,
        buffered: bool = True) -> tp.Tuple[int, str, str]:
    """
    Adapted from plumbum's TEE implementation.

    Plumbum's TEE does not allow access to the underlying popen object, which we
    need to properly handle keyboard interrupts. Therefore, we just copy the
    relevant portion of plumbum's implementation and create the popen object by
    ourself.
    """
    outbuf: tp.List[bytes] = []
    errbuf: tp.List[bytes] = []
    out = process.stdout
    err = process.stderr
    buffers = {out: outbuf, err: errbuf}
    tee_to = {out: sys.stdout, err: sys.stderr}
    done = False
    while not done:
        # After the process exits, we have to do one more
        # round of reading in order to drain any data in the
        # pipe buffer. Thus, we check poll() here,
        # unconditionally enter the read loop, and only then
        # break out of the outer loop if the process has
        # exited.
        done = process.poll() is not None

        # We continue this loop until we've done a full
        # `select()` call without collecting any input. This
        # ensures that our final pass -- after process exit --
        # actually drains the pipe buffers, even if it takes
        # multiple calls to read().
        progress = True
        while progress:
            progress = False
            ready, _, _ = select((out, err), (), ())
            # logging.info(f"Streams ready: {[r.fileno() for r in ready]}")
            for file_descriptor in ready:
                buf = buffers[file_descriptor]
                data, text = read_fd_decode_safely(file_descriptor, 4096)
                if not data:  # eof
                    continue
                progress = True

                # Python conveniently line-buffers stdout and stderr for
                # us, so all we need to do is write to them

                # This will automatically add up to three bytes if it cannot be
                # decoded
                tee_to[file_descriptor].write(text)

                # And then "unbuffered" is just flushing after each write
                if not buffered:
                    tee_to[file_descriptor].flush()

                buf.append(data)

    stdout = "".join([x.decode("utf-8") for x in outbuf])
    stderr = "".join([x.decode("utf-8") for x in errbuf])
    return process.returncode, stdout, stderr

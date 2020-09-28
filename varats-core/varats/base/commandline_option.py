"""Configuration option module."""
import abc
import typing as tp

from varats.base.configuration import Configuration


class CommandlineOption(abc.ABC):
    """Abstract class representing different kinds of command-line options,
    passed to tools like ls, e.g., `ls -l -a`."""

    @abc.abstractmethod
    def render(self, config: Configuration) -> str:
        """
        Render the configuration option to a command line string.

        Args:
            config: program configuration

        Returns: command line string for the given `Configuration`
        """


class CommandlineOptionSwitch(CommandlineOption):
    """Option switch is only included if a certain condition is met, otherwise,
    nothing."""

    def __init__(
        self, option_name: str, flag: str, condition: bool = True
    ) -> None:
        self.__option_name = option_name
        self.__flag = flag
        self.__condition = condition

    def render(self, config: Configuration) -> str:
        maybe_value = config.get_config_value(self.__option_name)
        if maybe_value is not None and (bool(maybe_value) == self.__condition):
            return self.__flag

        return ""


class CommandlineOptionFormat(CommandlineOption):
    """Option that is rendered from a format string, taking feature/option names
    as keys and rendering the corresponding stringified values, e.g., for
    "--{foo}" the feature/option name 'foo' is replaced with 'fast' for the
    config { 'foo': 'fast' }."""

    def __init__(
        self,
        option_name: str,
        flag_format_string: str,
        should_render: tp.Callable[[Configuration], bool] = lambda x: True
    ) -> None:
        self.__option_name = option_name
        self.__flag_format_string = flag_format_string
        self.__should_render = should_render

    def render(self, config: Configuration) -> str:
        if self.__should_render(config):
            return self.__flag_format_string.format_map(
                self.__config_to_string_dict(config)
            )
        return ""

    @staticmethod
    def __config_to_string_dict(config: Configuration) -> tp.Dict[str, str]:
        return {option.name: str(option.value) for option in config.options()}


class CommandlineOptionGroup(CommandlineOption):
    """Defines a sequence of `CommandlineOption`s keeping a strict order between
    the options."""

    def __init__(self, cli_options: tp.List[CommandlineOption]) -> None:
        self.__cli_options = cli_options

    def render(self, config: Configuration) -> str:
        return " ".join([
            option.render(config) for option in self.__cli_options
        ])


class CommandlineSpecification(CommandlineOptionGroup):
    """
    Specifies the different options that can be passed to a program. Take for
    example a simple specification for 'ls':

    ```code
    CommandlineSpecification(
        CommandlineOptionSwitch("list", "-l"),
        CommandlineOptionSwitch("human_readable", "-h")
    )
    ```

    This allows the user to enable the features 'list' or 'human_readable'
    adding '-l' or '-h' to the command line of 'ls' when executed.
    """


# Adds small class aliases to the module
CLOSwitch = CommandlineOptionSwitch
CLOFormat = CommandlineOptionFormat
CLOGroup = CommandlineOptionGroup
CLOSpec = CommandlineSpecification

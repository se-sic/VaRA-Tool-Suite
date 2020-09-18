"""Configuration map module."""
import abc
import logging
import typing as tp
from pathlib import Path

import yaml

from varats.base.configuration import Configuration
from varats.base.version_header import VersionHeader

LOG = logging.getLogger(__name__)

# TODO: options need testing


class CommandlineOption():
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
        if maybe_value and bool(maybe_value) == self.__condition:
            return self.__flag

        return ""


class CommandlineOptionFormat(CommandlineOption):
    """Option that is rendered from a format string, taking feature/option names
    as keys and rendering the corresponding stringified values, e.g., for
    "--{foo}" the feature/option name 'foo' is replaced with 'fast' for the
    config { 'foo': 'fast' }."""

    def _init__(
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

    def __init__(self, cli_options: tp.List[CommandlineOption]) -> None:
        super().__init__(cli_options)


# Adds small class aliases to the module
CLOSwitch = CommandlineOptionSwitch
CLOFormat = CommandlineOptionFormat
CLOGroup = CommandlineOptionGroup
CLOSpec = CommandlineSpecification


class ConfigurationMap():
    """A configuration map builds a relation between an unique ID and the
    corresponding project configuration."""

    def __init__(self) -> None:
        self.__confgurations: tp.Dict[int, Configuration] = dict()

    # TODO: impl class


def load_configuration_map(file_path: Path) -> ConfigurationMap:
    """
    Load a configuration map from a file.

    Args:
        file_path: to the configuration map file

    Returns: a new `ConfigurationMap` based on the parsed file
    """
    with open(file_path, 'r') as stream:
        documents = yaml.load_all(stream, Loader=yaml.CLoader)
        version_header = VersionHeader(next(documents))
        version_header.raise_if_not_type("ConfigurationMap")
        version_header.raise_if_version_is_less_than(1)

        return create_configuration_map_from_yaml_doc(next(documents))


def store_configuration_map(
    configuration_map: ConfigurationMap, file_path: Path
) -> None:
    """
    Store a `ConfigurationMap` to a file.

    Args:
        configuration_map: to store
        file_path: to the file
    """
    if file_path.suffix not in ["yml", "yaml"]:
        LOG.warning(
            "ConfigurationMap file path does not end in "
            ".yaml or .yml but dumped file is of type yaml."
        )

    with open(file_path, 'w') as stream:
        version_header = VersionHeader.from_version_number(
            "ConfigurationMap", 1
        )
        yaml.dump(version_header.get_dict(), stream)
        yaml.dump(get_configuration_map_as_yaml_doc(configuration_map), stream)


def create_configuration_map_from_yaml_doc(
    yaml_doc: tp.Dict[str, tp.Any]
) -> ConfigurationMap:
    """
    Create a configuration map from a yaml document.

    Args:
        yaml_doc: containing the configuration map

    Returns: a new `ConfigurationMap` based on the parsed doc
    """

    # TODO impl


def get_configuration_map_as_yaml_doc(
    configuration_map: ConfigurationMap
) -> tp.Dict[str, tp.Any]:
    """
    Dumps the `ConfigurationMap` as a yaml document.

    Args:
        configuration_map: to dump

    Returns: yaml representation of the configuration map
    """

    # TODO impl

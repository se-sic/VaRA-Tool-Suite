"""Configuration base classes, the correct implementation are provided by other
varats-* libraries."""
import abc
import json
import typing as tp
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

# Can be removed once https://peps.python.org/pep-0603/ is resolved.
from immutables import Map as FrozenMap
from immutables import MapMutation


class ConfigurationOption():
    """A configuration option for a software project."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The option name, refering to the feature from which this options
        stems."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abc.abstractmethod
    def value(self) -> str:
        """Currently set value of the option."""
        raise NotImplementedError  # pragma: no cover

    def __str__(self) -> str:
        return f"{self.name}: {str(self.value)}"

    def __bool__(self) -> bool:
        return bool(self.value)

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, ConfigurationOption):
            return (self.name == other.name) and (self.value == other.value)
        return False

    def __ne__(self, other: tp.Any) -> bool:
        return not self == other


class Configuration():
    """Represents a specific configuration of a project, e.g., encapsulating
    static and run-time options on how the project should be build."""

    @staticmethod
    @abc.abstractmethod
    def create_configuration_from_str(config_str: str) -> 'Configuration':
        """
        Creates a `Configuration` from its string representation.

        This function is the inverse to `dump_to_string` to reparse a
        configuration dumpred previously.

        Returns: new Configuration
        """

    @abc.abstractmethod
    def add_config_option(self, option: ConfigurationOption) -> None:
        """
        Adds a new key:value mapping to the configuration.

        Args:
            option_name: config key, i.e., feature name
            value: of the specified feature
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def set_config_option(self, option_name: str, value: str) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., feature name
            value: of the specified feature
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
        """
        Returns the set value for the given feature.

        Args:
            option_name: name of the feature to look up

        Returns: the currently set value for the feature
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def options(self) -> tp.List[ConfigurationOption]:
        """
        Get all configuration options.

        Returns: a list of all configuration options
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def dump_to_string(self) -> str:
        """
        Dumps the `Configuration` to a string.

        This function is the inverse to `create_configuration_from_str` to
        dump a configuration to be reparsed later.

        Returns: Configuration as a string
        """
        raise NotImplementedError  # pragma: no cover

    def __iter__(self) -> tp.Iterator[ConfigurationOption]:
        for option in self.options():
            yield option

    def __str__(self) -> str:
        return self.dump_to_string()


class DummyConfiguration(Configuration):
    """
    A special class that acts as a dummy in cases where users are not interested
    in working with ``Configuration`` s.

    It signals a project to use what ever default configuration values/setup it
    wants.
    """

    USAGE_ERROR_TEXT = """The dummy configuration does not provide any
functionality. If a DummyConfiguration shows up in you configuration related
part which accesses Configurations something is wrong with your setup."""

    @staticmethod
    def create_configuration_from_str(config_str: str) -> Configuration:
        """
        Creates a `Configuration` from its string representation.

        This function is the inverse to `dump_to_string` to reparse a
        configuration dumpred previously.

        Returns: new Configuration
        """
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def add_config_option(self, option: ConfigurationOption) -> None:
        """The dummy configuration does not add config options."""
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def set_config_option(self, option_name: str, value: str) -> None:
        """The dummy configuration does not set config options."""
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def get_config_value(self, option_name: str) -> tp.Optional[str]:
        """The dummy configuration does provide direct access to the
        configuration options."""
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def options(self) -> tp.List[ConfigurationOption]:
        """
        Get all configuration options.

        Returns: a list of all configuration options
        """
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def dump_to_string(self) -> str:
        """
        Dumps the `Configuration` to a string.

        This function is the inverse to `create_configuration_from_str` to
        dump a configuration to be reparsed later.

        Returns: Configuration as a string
        """
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)


@dataclass(frozen=True)
class ConfigurationOptionImpl(ConfigurationOption):
    """A configuration option of a software project."""

    _name: str
    _value: tp.Any

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> tp.Any:
        return self._value


def make_possible_type_conversion(option_value: str) -> tp.Any:
    """Converts string to correct type for special cases like bool or None."""
    if option_value.lower() == "true":
        return True
    if option_value.lower() == "false":
        return False
    if option_value.lower() == "none":
        return None

    return option_value


class ConfigurationImpl(Configuration):
    """A configuration of a software project."""

    @staticmethod
    def create_configuration_from_str(config_str: str) -> Configuration:
        """
        Creates a `Configuration` from its string representation.

        This function is the inverse to `dump_to_string` to reparse a
        configuration dumped previously.

        Returns: new Configuration
        """
        loaded_dict = json.loads(config_str)
        config = ConfigurationImpl()
        for option_name, option_value in loaded_dict.items():

            if option_value is not False and option_value is not True and \
                    not isinstance(option_value, int):
                option_value = make_possible_type_conversion(
                    option_value.strip()
                )
            config.add_config_option(
                ConfigurationOptionImpl(option_name.strip(), option_value)
            )

        return config

    def __init__(self) -> None:
        self.__config_values: tp.Union[MapMutation,
                                       FrozenMap] = FrozenMap().mutate()

    def add_config_option(self, option: ConfigurationOption) -> None:
        """
        Adds a new key:value mapping to the configuration.

        Args:
            option: the feature to add
        """
        self.__config_values[option.name] = option

    def set_config_option(self, option_name: str, value: str) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., option/feature name
            value: of the specified feature
        """
        self.add_config_option(ConfigurationOptionImpl(option_name, value))

    def get_config_value(self, option_name: str) -> tp.Optional[str]:
        """
        Returns the set value for the given feature.

        Args:
            option_name: name of the option/feature to look up

        Returns: set value for the feature
        """
        if option_name in self.__config_values:
            return self.__config_values[option_name].value

        return None

    def options(self) -> tp.List[ConfigurationOption]:
        if hasattr(self.__config_values, "values"):
            return list(self.__config_values.values())
        # Workaround mutable maps cannot be iterated yet
        # https://github.com/MagicStack/immutables/issues/55
        return list(self.__config_values.finish().values())

    def dump_to_string(self) -> str:
        if hasattr(self.__config_values, "values"):
            return json.dumps({
                idx[1].name: idx[1].value
                for idx in self.__config_values.items()
            })
        # Workaround mutable maps cannot be iterated yet
        # https://github.com/MagicStack/immutables/issues/55
        return json.dumps({
            idx[1].name: idx[1].value
            for idx in self.__config_values.finish().items()
        })

    def freeze(self) -> 'FrozenConfigurationImpl':
        self.__config_values = self.__config_values.finish()
        return FrozenConfigurationImpl(self)

    def unfreeze(self) -> None:
        self.__config_values = self.__config_values.mutate()


class FrozenConfigurationImpl:
    """Same as ConfigurationImpl but hashable."""

    def __init__(self, configuration_impl: ConfigurationImpl) -> None:
        self.configuration_impl = configuration_impl

    def __getattr__(self, __name: str) -> Any:
        return getattr(
            self.configuration_impl,
            __name.replace(self.__class__.__name__, ConfigurationImpl.__name__)
        )

    def __hash__(self) -> tp.Any:
        return self.__config_values.__hash__()

    def __deepcopy__(self, memo) -> ConfigurationImpl:
        result = deepcopy(self.configuration_impl, memo)
        result.unfreeze()
        return result

    def add_config_option(self, option: ConfigurationOption) -> None:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tp.Mapping):
            if len(self.__config_values) != len(other):
                return False
            for item in self.__config_values:
                if item not in other:
                    return False
            return True
        return False

    def __iter__(self) -> tp.Iterator[ConfigurationOption]:
        for option in self.options():
            yield option


class PlainConfigurationOption(ConfigurationOptionImpl):
    """A configuration option from plain text."""

    def __init__(self, value: str) -> None:
        super().__init__(value.lstrip("-"), value)


class PlainCommandlineConfiguration(ConfigurationImpl):
    """
    Simple configuration format where command line args are directly written
    into the file.

    Example: '["--foo", "--bar"]'
    """

    def __init__(self, config_str_list: tp.List[str]) -> None:
        super().__init__()
        for config_str in config_str_list:
            self.add_config_option(PlainConfigurationOption(config_str))

    @staticmethod
    def create_configuration_from_str(config_str: str) -> Configuration:
        config_str_list = json.loads(config_str)
        return PlainCommandlineConfiguration(config_str_list)

    def dump_to_string(self) -> str:
        return " ".join(map(lambda option: option.value, self.options()))

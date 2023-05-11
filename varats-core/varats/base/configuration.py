"""Configuration base classes, the correct implementation are provided by other
varats-* libraries."""
import abc
import json
import typing as tp
from copy import deepcopy
from dataclasses import dataclass


class ConfigurationOption:
    """A configuration option for a software project."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The option name, refering to the feature from which this options
        stems."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abc.abstractmethod
    def value(self) -> tp.Any:
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


class Configuration:
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
    def set_config_option(self, option_name: str, value: tp.Any) -> None:
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

    @abc.abstractmethod
    def freeze(self) -> 'FrozenConfiguration':
        """
        Returns an unmodifiable (hashable) version of the configuration. Useful
        when you want to add a 'Configuration' as key to a 'dict' or as element
        to a 'set'.

        Returns: 'FrozenConfiguration'
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def unfreeze(self) -> 'Configuration':
        """
        Returns an unmodifiable (hashable) version of the configuration.

        Returns: 'Configuration'
        """
        raise NotImplementedError  # pragma: no cover

    def __str__(self) -> str:
        return self.dump_to_string()

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, Configuration):
            return set(self.options()) == set(other.options())
        if isinstance(other, tp.Mapping):
            if len(self.options()) == len(other):
                for option in self.options():
                    if option.name not in other:
                        return False
                    if isinstance(other[option.name], bool):
                        if bool(option.value) != other[option.name]:
                            return False
                    else:
                        if option.value != other[option.name]:
                            return False
                return True
        return False

    def __ne__(self, other: tp.Any) -> bool:
        return not self == other


class FrozenConfiguration(Configuration):
    """
    An immutable hashable version of the configuration.

    Can be added as key to a 'dict' or as element to a 'set'.
    """

    def __init__(self, configuration: Configuration) -> None:
        self.__configuration = configuration

    @staticmethod
    def create_configuration_from_str(config_str: str) -> Configuration:
        raise NotImplementedError

    def options(self) -> tp.List[ConfigurationOption]:
        return self.__configuration.options()

    def add_config_option(self, option: ConfigurationOption) -> None:
        raise NotImplementedError

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        raise NotImplementedError

    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
        return self.__configuration.get_config_value(option_name)

    def dump_to_string(self) -> str:
        return self.__configuration.dump_to_string()

    def freeze(self) -> 'FrozenConfiguration':
        return self

    def unfreeze(self) -> Configuration:
        return deepcopy(self.__configuration)

    def __hash__(self) -> int:
        return hash(frozenset(self.options()))


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

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        """The dummy configuration does not set config options."""
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
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

    def freeze(self) -> FrozenConfiguration:
        raise AssertionError(DummyConfiguration.USAGE_ERROR_TEXT)

    def unfreeze(self) -> Configuration:
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

            def make_possible_type_conversion(option_value: str) -> tp.Any:
                """Converts string to correct type for special cases like bool
                or None."""
                if option_value.lower() == "true":
                    return True
                if option_value.lower() == "false":
                    return False
                if option_value.lower() == "none":
                    return None

                return option_value

            if (
                option_value is not False and option_value is not True and
                not isinstance(option_value, int)
            ):
                option_value = make_possible_type_conversion(
                    option_value.strip()
                )
            config.add_config_option(
                ConfigurationOptionImpl(option_name.strip(), option_value)
            )

        return config

    def __init__(self) -> None:
        self.__config_values: tp.Dict[str, ConfigurationOption] = {}

    def add_config_option(self, option: ConfigurationOption) -> None:
        """
        Adds a new key:value mapping to the configuration.

        Args:
            option: the feature to add
        """
        self.__config_values[option.name] = option

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., option/feature name
            value: of the specified feature
        """
        self.add_config_option(ConfigurationOptionImpl(option_name, value))

    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
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
        return list(self.__config_values.values())

    def dump_to_string(self) -> str:
        return json.dumps({
            idx[1].name: idx[1].value for idx in self.__config_values.items()
        })

    def freeze(self) -> FrozenConfiguration:
        return FrozenConfiguration(deepcopy(self))

    def unfreeze(self) -> Configuration:
        return self


class PlainConfigurationOption(ConfigurationOptionImpl):

    def __init__(self, value: str) -> None:
        super().__init__(value.lstrip("-"), value)


class PlainCommandlineConfiguration(Configuration):
    """
    Simple configuration format where command line args are directly written
    into the file.

    Example: '["--foo", "--bar"]'
    """

    def __init__(self, config_str_list: tp.List[str]) -> None:
        self.__config_str_list: tp.List[ConfigurationOption] = list(
            map(PlainConfigurationOption, config_str_list)
        )

    @staticmethod
    def create_configuration_from_str(config_str: str) -> Configuration:
        config_str_list = json.loads(config_str)
        return PlainCommandlineConfiguration(config_str_list)

    def dump_to_string(self) -> str:
        return " ".join(
            map(lambda option: str(option.value), self.__config_str_list)
        )

    def options(self) -> tp.List[ConfigurationOption]:
        return self.__config_str_list

    def freeze(self) -> "FrozenConfiguration":
        return FrozenConfiguration(deepcopy(self))

    def add_config_option(self, option: ConfigurationOption) -> None:
        self.__config_str_list.append(option)

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        self.add_config_option(ConfigurationOptionImpl(option_name, value))

    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
        for option in self.options():
            if option.name == option_name:
                return option.value
        return None

    def unfreeze(self) -> Configuration:
        return self

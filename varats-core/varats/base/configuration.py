"""Configuration base classes, the correct implementation are provided by other
varats-* libraries."""
import abc
import typing as tp


class ConfigurationOption():

    @abc.abstractproperty
    def name(self) -> str:
        """The option name, refering to the feature from which this options
        stems."""

    @abc.abstractproperty
    def value(self) -> tp.Any:
        """Current set value of the option."""

    def __str__(self) -> str:
        return f"{self.name}: {str(self.value)}"


class Configuration():

    # TODO: missing serialzie

    @abc.abstractmethod
    def add_config_option(self, option: ConfigurationOption) -> None:
        """
        Adds a new key:value mapping to the configuration.

        Args:
            option_name: config key, i.e., feature name
            value: of the specified feature
        """

    @abc.abstractmethod
    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., feature name
            value: of the specified feature
        """

    @abc.abstractmethod
    def get_config_value(self, option_name: str) -> tp.Optional[tp.Any]:
        """
        Returns the set value for the given feature.

        Args:
            option_name: name of the feature to look up

        Returns: the currently set value for the feature
        """

    @abc.abstractmethod
    def options(self) -> tp.List[ConfigurationOption]:
        """
        Get all configuration options.

        Returns: a list of all configuration options
        """


class TestConfigurationOptionImpl(ConfigurationOption):

    def __init__(self, name: str, value: tp.Any) -> None:
        self.__name = name
        self.__value = value

    def name(self) -> str:
        return self.__name

    def value(self) -> tp.Any:
        self.__value


class TestConfigurationImpl(Configuration):

    def __init__(self) -> None:
        self.__config_values: tp.Dict[str, ConfigurationOption] = {
            "foo": TestConfigurationOptionImpl("foo", "fooval"),
            "bar": TestConfigurationOptionImpl("bar", "barval")
        }

    def add_config_option(self, option: ConfigurationOption) -> None:
        """
        Adds a new key:value mapping to the configuration.

        Args:
            option_name: config key, i.e., feature name
            value: of the specified feature
        """
        self.__config_values[option.name] = option

    def set_config_value(self, option_name, value) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., option/feature name
            value: of the specified feature
        """
        self.add_config_option(TestConfigurationOptionImpl(option_name, value))

    def get_config_value(self, option_name) -> tp.Any:
        """
        Returns the set value for the given feature.

        Args:
            option_name: name of the option/feature to look up

        Returns: set value for the feature
        """
        return self.__config_values[option_name]

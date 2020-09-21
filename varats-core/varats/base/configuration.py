"""Configuration base classes, the correct implementation are provided by other
varats-* libraries."""
import abc
import typing as tp


class ConfigurationOption():
    """A configuration option for a software project."""

    @abc.abstractproperty
    def name(self) -> str:
        """The option name, refering to the feature from which this options
        stems."""

    @abc.abstractproperty
    def value(self) -> tp.Any:
        """Current set value of the option."""

    def __str__(self) -> str:
        return f"{self.name}: {str(self.value)}"

    def __bool__(self) -> bool:
        return bool(self.value)


class Configuration():
    """Represents a specific configuration of a project, e.g., encapsulating
    static and run-time options on how the project should be build."""

    @staticmethod
    @abc.abstractstaticmethod
    def create_configuration_from_str(config_str: str) -> 'Configuration':
        """
        Creates a `Configuration` from it's string representation.

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

    @abc.abstractmethod
    def dump_to_string(self) -> str:
        """
        Dumps the `Configuration` to a string.

        This function is the inverse to `create_configuration_from_str` to
        dump a configuration to be reparsed later.

        Returns: Configuration as a string
        """

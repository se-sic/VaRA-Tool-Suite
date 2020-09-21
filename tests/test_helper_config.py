"""Test helper module for Configuration classes."""
import typing as tp

from varats.base.configuration import Configuration, ConfigurationOption


class TestConfigurationOptionImpl(ConfigurationOption):
    """Small `ConfigurationOption` implementation for testing."""

    def __init__(self, name: str, value: tp.Any) -> None:
        self.__name = name
        self.__value = value

    @property
    def name(self) -> str:
        return self.__name

    @property
    def value(self) -> tp.Any:
        return self.__value


class TestConfigurationImpl(Configuration):
    """Small `Configuration` implementation for testing."""

    @staticmethod
    def create_test_config() -> 'TestConfigurationImpl':
        """Create a small test Configuration."""
        test_config = TestConfigurationImpl()
        test_config.add_config_option(TestConfigurationOptionImpl("foo", True))
        test_config.add_config_option(TestConfigurationOptionImpl("bar", False))
        test_config.add_config_option(
            TestConfigurationOptionImpl("bazz", "bazz-value")
        )
        return test_config

    def __init__(self) -> None:
        self.__config_values: tp.Dict[str, ConfigurationOption] = dict()

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

    def get_config_value(self, option_name) -> tp.Optional[tp.Any]:
        """
        Returns the set value for the given feature.

        Args:
            option_name: name of the option/feature to look up

        Returns: set value for the feature
        """
        if option_name in self.__config_values:
            return self.__config_values[option_name]

        return None

    def options(self) -> tp.List[ConfigurationOption]:
        return list(self.__config_values.values())

    def dump_to_string(self):
        raise NotImplementedError

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        raise NotImplementedError

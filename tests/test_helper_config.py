"""Test helper module for Configuration classes."""
import json
import typing as tp

from varats.base.configuration import Configuration, ConfigurationOption


class ConfigurationOptionTestImpl(ConfigurationOption):
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


class ConfigurationTestImpl(Configuration):
    """Small `Configuration` implementation for testing."""

    @staticmethod
    def create_test_config() -> 'ConfigurationTestImpl':
        """Create a small test Configuration."""
        test_config = ConfigurationTestImpl()
        test_config.add_config_option(ConfigurationOptionTestImpl("foo", True))
        test_config.add_config_option(ConfigurationOptionTestImpl("bar", False))
        test_config.add_config_option(
            ConfigurationOptionTestImpl("bazz", "bazz-value")
        )
        return test_config

    @staticmethod
    def create_configuration_from_str(config_str: str) -> 'Configuration':
        """
        Creates a `Configuration` from its string representation.

        This function is the inverse to `dump_to_string` to reparse a
        configuration dumped previously.

        Returns: new Configuration
        """
        loaded_dict = json.loads(config_str.replace('\'', "\""))
        config = ConfigurationTestImpl()
        for _, option in loaded_dict.items():
            option_name, option_value = option.split(":", maxsplit=1)

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

            config.add_config_option(
                ConfigurationOptionTestImpl(
                    option_name.strip(),
                    make_possible_type_conversion(option_value.strip())
                )
            )

        return config

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

    def set_config_option(self, option_name: str, value: tp.Any) -> None:
        """
        Sets the value of a `ConfigurationOption` with the corresponding key.

        Args:
            option_name: config key, i.e., option/feature name
            value: of the specified feature
        """
        self.add_config_option(ConfigurationOptionTestImpl(option_name, value))

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

    def dump_to_string(self) -> str:
        return str({
            str(idx[0]): str(idx[1]) for idx in self.__config_values.items()
        })

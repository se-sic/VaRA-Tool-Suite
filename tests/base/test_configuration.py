"""Test module for Configuration tests."""

import unittest

import varats.base.commandline_option as CO
from tests.test_helper_config import (
    ConfigurationOptionTestImpl,
    ConfigurationTestImpl,
)
from varats.base.configuration import Configuration


class TestConfigurationOption(unittest.TestCase):
    """Test if ConfigurationOption is working."""

    def test_basic_configuration_option_setup(self) -> None:
        """Test of the basic interface of configuration options works."""
        config_option = ConfigurationOptionTestImpl("foo", 42)

        self.assertEqual(config_option.name, "foo")
        self.assertEqual(config_option.value, 42)

    def test_to_str(self) -> None:
        """Test to convert config option to string."""
        config_option = ConfigurationOptionTestImpl("foo", 42)

        self.assertEqual(str(config_option), "foo: 42")

    def test_convert_to_bool(self) -> None:
        """Test to convert config option to bool."""
        config_option_int = ConfigurationOptionTestImpl("foo", 42)
        config_option_bool = ConfigurationOptionTestImpl("foo", False)

        self.assertEqual(bool(config_option_int), True)
        self.assertEqual(bool(config_option_bool), False)

    def test_equality_same(self) -> None:
        """Test to compare config option to to each other."""
        config_option_int = ConfigurationOptionTestImpl("foo", 42)
        config_option_int_2 = ConfigurationOptionTestImpl("foo", 42)

        self.assertTrue(config_option_int == config_option_int_2)
        self.assertFalse(config_option_int != config_option_int_2)

    def test_equality_different(self) -> None:
        """Test to compare config option to to each other."""
        config_option_int = ConfigurationOptionTestImpl("foo", 42)
        config_option_bool = ConfigurationOptionTestImpl("foo", False)

        self.assertFalse(config_option_int == config_option_bool)
        self.assertTrue(config_option_int != config_option_bool)

    def test_equality_othertypes(self) -> None:
        """Test to compare config option to to each other."""
        config_option_int = ConfigurationOptionTestImpl("foo", 42)
        other_object = 42

        self.assertFalse(config_option_int == other_object)
        self.assertTrue(config_option_int != other_object)


class TestConfiguration(unittest.TestCase):
    """Test if Configuration is working."""

    def test_to_str(self) -> None:
        """Test to convert config to string."""
        config = ConfigurationTestImpl.create_test_config()

        self.assertEqual(str(config), config.dump_to_string())

"""Test module for Configuration tests."""

import unittest

from tests.helper_utils import ConfigurationHelper
from varats.base.configuration import (
    DummyConfiguration,
    ConfigurationImpl,
    ConfigurationOptionImpl,
    FrozenConfiguration,
)


class TestConfigurationOption(unittest.TestCase):
    """Test if ConfigurationOption is working."""

    def test_basic_configuration_option_setup(self) -> None:
        """Test of the basic interface of configuration options works."""
        config_option = ConfigurationOptionImpl("foo", 42)

        self.assertEqual(config_option.name, "foo")
        self.assertEqual(config_option.value, 42)

    def test_to_str(self) -> None:
        """Test to convert config option to string."""
        config_option = ConfigurationOptionImpl("foo", 42)

        self.assertEqual(str(config_option), "foo: 42")

    def test_set_config_option(self) -> None:
        """Test to set the value of a configuration option."""
        config = ConfigurationHelper.create_test_config()
        config.set_config_option("foo", False)
        self.assertFalse(config.get_config_value("foo"))

    def test_convert_to_bool(self) -> None:
        """Test to convert config option to bool."""
        config_option_int = ConfigurationOptionImpl("foo", 42)
        config_option_bool = ConfigurationOptionImpl("foo", False)

        self.assertEqual(bool(config_option_int), True)
        self.assertEqual(bool(config_option_bool), False)

    def test_equality_same(self) -> None:
        """Test to compare config option to to each other."""
        config_option_int = ConfigurationOptionImpl("foo", 42)
        config_option_int_2 = ConfigurationOptionImpl("foo", 42)

        self.assertTrue(config_option_int == config_option_int_2)
        self.assertFalse(config_option_int != config_option_int_2)

    def test_equality_different(self) -> None:
        """Test to compare config option to to each other."""
        config_option_int = ConfigurationOptionImpl("foo", 42)
        config_option_bool = ConfigurationOptionImpl("foo", False)

        self.assertFalse(config_option_int == config_option_bool)
        self.assertTrue(config_option_int != config_option_bool)

    def test_equality_othertypes(self) -> None:
        """Test to compare config option to each other."""
        config_option_int = ConfigurationOptionImpl("foo", 42)
        other_object = 42

        self.assertFalse(config_option_int == other_object)
        self.assertTrue(config_option_int != other_object)


class TestConfiguration(unittest.TestCase):
    """Test if Configuration is working."""

    def test_to_str(self) -> None:
        """Test to convert config to string."""
        config = ConfigurationHelper.create_test_config()

        self.assertEqual(str(config), config.dump_to_string())

    def test_equality_same(self) -> None:
        """Test to compare configuration to each other."""
        config = ConfigurationImpl()
        config.add_config_option(ConfigurationOptionImpl("foo", 42))
        config_2 = ConfigurationImpl()
        config_2.add_config_option(ConfigurationOptionImpl("foo", 42))

        self.assertTrue(config == config_2)
        self.assertFalse(config != config_2)

    def test_equality_different(self) -> None:
        """Test to compare configuration to to each other."""
        config = ConfigurationImpl()
        config.add_config_option(ConfigurationOptionImpl("foo", 42))
        config_2 = ConfigurationImpl()
        config_2.add_config_option(ConfigurationOptionImpl("foo", False))

        self.assertFalse(config == config_2)
        self.assertTrue(config != config_2)

    def test_equality_mapping(self) -> None:
        """Test to compare configuration to a mapping."""
        config = ConfigurationImpl()
        config.add_config_option(ConfigurationOptionImpl("foo", 42))

        mapping_identical = {"foo": 42}
        mapping_not_identical = {"foo": 43}
        mapping_interpreted = {"foo": True}
        mapping_not_interpreted = {"foo": False}

        self.assertTrue(config == mapping_identical)
        self.assertFalse(config != mapping_identical)

        self.assertFalse(config == mapping_not_identical)
        self.assertTrue(config != mapping_not_identical)

        self.assertTrue(config == mapping_interpreted)
        self.assertFalse(config != mapping_interpreted)

        self.assertFalse(config == mapping_not_interpreted)
        self.assertTrue(config != mapping_not_interpreted)

        config_2 = ConfigurationImpl()
        config_2.add_config_option(ConfigurationOptionImpl("foo", False))

        self.assertFalse(config_2 == mapping_interpreted)
        self.assertTrue(config_2 != mapping_interpreted)

        self.assertTrue(config_2 == mapping_not_interpreted)
        self.assertFalse(config_2 != mapping_not_interpreted)

    def test_equality_othertypes(self) -> None:
        """Test to compare configuration to each other."""
        config = ConfigurationImpl()
        config.add_config_option(ConfigurationOptionImpl("foo", 42))
        other_object = 42

        self.assertFalse(config == other_object)
        self.assertTrue(config != other_object)


class TestDummyConfiguration(unittest.TestCase):
    """Test if the Dummy Configuration does not allow any interface usage."""

    def test_crash_create_config_from_str(self) -> None:
        with self.assertRaises(AssertionError):
            DummyConfiguration.create_configuration_from_str("")

    def test_crash_add_config_option(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.add_config_option(ConfigurationOptionImpl("foo", 42))

    def test_crash_set_config_option(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.set_config_option("foo", 42)

    def test_crash_get_config_value(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.get_config_value("foo")

    def test_crash_options(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.options()

    def test_crash_dump_to_string(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.dump_to_string()

    def test_crash_freeze(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.freeze()

    def test_crash_unfreeze(self) -> None:
        with self.assertRaises(AssertionError):
            d_config = DummyConfiguration()
            d_config.unfreeze()


class TestFrozenConfiguration(unittest.TestCase):
    """Test freeze and unfreeze methods of a FrozenConfiguration."""

    def test_freeze_and_unfreeze(self) -> None:
        config = ConfigurationImpl()
        config.add_config_option(ConfigurationOptionImpl("foo", 42))
        frozen_config = config.freeze()

        self.assertTrue(isinstance(frozen_config, FrozenConfiguration))
        self.assertTrue(frozen_config == config)
        self.assertTrue(frozen_config is frozen_config.freeze())
        self.assertFalse(frozen_config is config)

        with self.assertRaises(NotImplementedError):
            frozen_config.add_config_option(ConfigurationOptionImpl("foo", 42))

        unfrozen_config = frozen_config.unfreeze()
        self.assertTrue(isinstance(unfrozen_config, ConfigurationImpl))
        self.assertTrue(unfrozen_config == config)
        self.assertTrue(unfrozen_config is unfrozen_config.unfreeze())
        self.assertFalse(unfrozen_config is frozen_config)

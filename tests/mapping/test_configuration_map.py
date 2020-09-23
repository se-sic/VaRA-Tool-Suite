"""Test module for ConfigurationMap tests."""

import typing as tp
import unittest

from tests.test_helper_config import TestConfigurationImpl
from varats.mapping.configuration_map import ConfigurationMap


class TestConfigurationMap(unittest.TestCase):
    """Test if ConfigurationMap is working."""

    def test_add_get_config(self) -> None:
        """Tests if we can add and retrieve a config from the map."""
        config_map = ConfigurationMap()
        test_config = TestConfigurationImpl()

        config_id = config_map.add_configuration(test_config)

        self.assertEqual(0, config_id)
        self.assertEqual(test_config, config_map.get_configuration(config_id))

    def test_add_get_multiple_configs(self) -> None:
        """Tests if we can add and retrieve multiple configs from the map."""
        config_map = ConfigurationMap()
        test_config_1 = TestConfigurationImpl()
        test_config_2 = TestConfigurationImpl()
        test_config_3 = TestConfigurationImpl()

        config_id_1 = config_map.add_configuration(test_config_1)
        config_id_2 = config_map.add_configuration(test_config_2)
        config_id_3 = config_map.add_configuration(test_config_3)

        self.assertEqual(0, config_id_1)
        self.assertEqual(1, config_id_2)
        self.assertEqual(2, config_id_3)

        self.assertEqual(
            test_config_3, config_map.get_configuration(config_id_3)
        )
        self.assertEqual(
            test_config_1, config_map.get_configuration(config_id_1)
        )
        self.assertEqual(
            test_config_2, config_map.get_configuration(config_id_2)
        )

    def test_inter_configs(self) -> None:
        """Test if we can iterate over all configurations."""
        config_map = ConfigurationMap()
        test_config_1 = TestConfigurationImpl()
        test_config_2 = TestConfigurationImpl()
        test_config_3 = TestConfigurationImpl()

        config_map.add_configuration(test_config_1)
        config_map.add_configuration(test_config_2)
        config_map.add_configuration(test_config_3)

        self.assertEqual(3, len(config_map.configurations()))
        self.assertSetEqual({test_config_1, test_config_2, test_config_3},
                            set(config_map.configurations()))

    def test_inter_id_config_tuples(self) -> None:
        """Test if we can iterate over all id configuration pairs."""
        config_map = ConfigurationMap()
        test_config_1 = TestConfigurationImpl()
        test_config_2 = TestConfigurationImpl()
        test_config_3 = TestConfigurationImpl()

        config_map.add_configuration(test_config_1)
        config_map.add_configuration(test_config_2)
        config_map.add_configuration(test_config_3)

        self.assertEqual(3, len(config_map.id_config_tuples()))
        self.assertSetEqual({(0, test_config_1), (1, test_config_2),
                             (2, test_config_3)},
                            set(config_map.id_config_tuples()))

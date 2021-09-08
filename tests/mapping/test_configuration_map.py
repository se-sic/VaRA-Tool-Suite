"""Test module for ConfigurationMap tests."""

import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from tests.test_utils import ConfigurationHelper
from varats.base.configuration import (
    DummyConfiguration,
    ConfigurationImpl,
    ConfigurationOptionImpl,
)
from varats.mapping.configuration_map import (
    ConfigurationMap,
    store_configuration_map,
    load_configuration_map,
    create_configuration_map_from_yaml_doc,
)

YAML_DOC_CONFIG_HEADER = """---
DocType: ConfigurationMap
Version: 1
...
"""
YAML_DOC_CONFIG_MAP = """---
0: '{"foo": true, "bar": false, "bazz": "bazz-value", "buzz": "None"}'
1: '{}'
2: '{}'
...
"""


class TestConfigurationMap(unittest.TestCase):
    """Test if ConfigurationMap is working."""

    def test_add_get_config(self) -> None:
        """Tests if we can add and retrieve a config from the map."""
        config_map = ConfigurationMap()
        test_config = ConfigurationImpl()

        config_id = config_map.add_configuration(test_config)

        self.assertEqual(0, config_id)
        self.assertEqual(test_config, config_map.get_configuration(config_id))

    def test_get_dummy_config(self) -> None:
        """Tests if we can retrieve the special ``DummyConfiguration`` from the
        map."""
        config_map = ConfigurationMap()

        self.assertEqual(
            type(
                config_map.get_configuration(ConfigurationMap.DUMMY_CONFIG_ID)
            ), DummyConfiguration
        )

    def test_add_get_multiple_configs(self) -> None:
        """Tests if we can add and retrieve multiple configs from the map."""
        config_map = ConfigurationMap()
        test_config_1 = ConfigurationImpl()
        test_config_2 = ConfigurationImpl()
        test_config_3 = ConfigurationImpl()

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
        test_config_1 = ConfigurationImpl()
        test_config_2 = ConfigurationImpl()
        test_config_3 = ConfigurationImpl()

        config_map.add_configuration(test_config_1)
        config_map.add_configuration(test_config_2)
        config_map.add_configuration(test_config_3)

        self.assertEqual(3, len(config_map.configurations()))
        self.assertSetEqual({test_config_1, test_config_2, test_config_3},
                            set(config_map.configurations()))

    def test_inter_id_config_tuples(self) -> None:
        """Test if we can iterate over all id configuration pairs."""
        config_map = ConfigurationMap()
        test_config_1 = ConfigurationImpl()
        test_config_2 = ConfigurationImpl()
        test_config_3 = ConfigurationImpl()

        config_map.add_configuration(test_config_1)
        config_map.add_configuration(test_config_2)
        config_map.add_configuration(test_config_3)

        self.assertEqual(3, len(config_map.id_config_tuples()))
        self.assertSetEqual({(0, test_config_1), (1, test_config_2),
                             (2, test_config_3)},
                            set(config_map.id_config_tuples()))


class TestConfigurationMapStoreAndLoad(unittest.TestCase):
    """Test if ConfigurationMap can be stored and loaded."""

    @classmethod
    def setUpClass(cls):
        """Setup test ConfigurationMap."""
        cls.config_map = ConfigurationMap()
        cls.test_config_1 = ConfigurationHelper.create_test_config()
        cls.test_config_2 = ConfigurationImpl()
        cls.test_config_3 = ConfigurationImpl()

        cls.config_id_1 = cls.config_map.add_configuration(cls.test_config_1)
        cls.config_id_2 = cls.config_map.add_configuration(cls.test_config_2)
        cls.config_id_3 = cls.config_map.add_configuration(cls.test_config_3)

    def test_store_configuration_map(self) -> None:
        """Tests if we can store a configuration map correctly into a file."""
        with NamedTemporaryFile('r') as yaml_output_file:
            store_configuration_map(
                self.config_map, Path(yaml_output_file.name)
            )

            self.assertEqual(
                YAML_DOC_CONFIG_HEADER + YAML_DOC_CONFIG_MAP,
                "".join(yaml_output_file.readlines())
            )

    @mock.patch("builtins.open", create=True)
    def test_load_configuration_map(self, mock_open) -> None:
        """Tests if we can load a stored configuration map correctly from a
        file."""
        mock_open.side_effect = [
            mock.mock_open(
                read_data=YAML_DOC_CONFIG_HEADER + YAML_DOC_CONFIG_MAP
            ).return_value
        ]

        config_map = load_configuration_map(
            Path("fake_file_path"), ConfigurationImpl
        )

        self.assertSetEqual({0, 1, 2}, set(config_map.ids()))
        self.assertTrue(config_map.get_configuration(0) is not None)

    def test_create_configuration_map_from_dict(self) -> None:
        """Tests if we can create a `ConfigurationMap` from a dict, similar to a
        yaml doc."""
        config_map = create_configuration_map_from_yaml_doc({
            '0': '{"foo": "True", "bar": "False", "bazz": "bazz-value"}',
            '1': "{}"
        }, ConfigurationImpl)

        self.assertSetEqual({0, 1}, set(config_map.ids()))
        config = config_map.get_configuration(0)
        self.assertTrue(config is not None)
        if config:
            self.assertEqual(
                ConfigurationOptionImpl("foo", True),
                config.get_config_value("foo")
            )
        self.assertTrue(config_map.get_configuration(1) is not None)
